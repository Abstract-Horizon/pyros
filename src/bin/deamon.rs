// use clap::{Arg, App};
use clap::Parser;

use std::collections::HashMap;
use std::fs;
use std::io::Error;
use std::path::Path;
use std::process;
use std::process::{Stdio};

use futures::stream::{FuturesUnordered, StreamExt};

use tokio::{io::{BufReader, AsyncBufReadExt}, process::Command};

use tokio::signal;

use rumqttc::ConnectionError;

use pyros::mqtt_client::MQTTClient;


fn pyros_test_topic(msg: rumqttc::Publish, _mqtt_client: &MQTTClient) -> () {
    println!("Received message on {:?}: {:?}", msg.topic, msg.payload)
}

#[derive(Parser, Debug)]
#[clap(author, version, about, long_about = None)]

#[clap(name = "PyROS")]
#[clap(author = "Daniel Sendula")]
#[clap(version = "2.0.1")]
#[clap(about = "Core deamon for PyROS", long_about = None)]
struct Args {
    #[clap(short = 'd', long = "home-dir", value_parser)]
    home_dir: Option<String>,

    #[clap(short = 'h', long, value_parser)]
    host: Option<String>,

    #[clap(short = 'c', long, value_parser)]
    command: Option<String>,

    #[clap(short, long, value_parser, default_value_t = 0)]
    verbose: u8,
}

#[tokio::main(flavor = "current_thread")]
async fn main() {

    let args = Args::parse();

    let home_dir_arg = args.home_dir.as_deref().unwrap_or(".");
    let home_dir = match fs::canonicalize(Path::new(home_dir_arg)) {
        Ok(p) => p,
        Err(..) => {
            eprintln!("Supplied homedir {} does not exist", home_dir_arg);
            process::exit(1);
        }
    };

    println!("Verbosity level set to {}", args.verbose);
    println!("Home dir is {}", &home_dir.display());

    let config_file = home_dir.join("pyros.config");

    let mut config: HashMap<String, String> = HashMap::new();
    config = pyros::config::load_config(&config_file, config)
        .expect(format!("Cannot read config file {:?}", config_file).as_ref());

    let host_address = args.host.as_deref().unwrap_or("127.0.0.1").to_owned();
    let host_address = config.get("mqtt.host").unwrap_or(&host_address);

    println!("MQTT broker is {}", &host_address);

    let mut mqtt_client = MQTTClient::new(host_address);

    println!("Running process notification thread, too...");

    mqtt_client.subscribe("hello", pyros_test_topic).await;

    let mut last_error: Option<ConnectionError> = None;

    let mut futures = FuturesUnordered::new();

    // let mut stdout_reader: Option<BufReader<&mut ChildStdout>> = None;
    // let mut buf = vec![];

    if let Some(command_to_run) = args.command.as_ref() {
        let mut child = Command::new(command_to_run)
            // .args(&args)
            .stdout(Stdio::piped())
            .spawn()
            .unwrap();

        let stdout = child.stdout.take().expect("child did not have a handle to stdout");

        let mut stdout_reader = BufReader::new(stdout).lines();

        // let mut buf = vec![];
        // let stdout_lines = stdout_reader.lines();

                    // _ = stdout_reader.unwrap().lines().read_until(b'\n', &mut buf), if stdout_reader.is_some() => {
        futures.push(async move {
            // while stdout_reader.unwrap().lines().read_until(b'\n', &mut buf) {
            //
            // }
            while let Some(line) = stdout_reader.next_line().await? {
                println!("Stderr line: {}", line);
            }
            Ok::<&str, Error>("Finished")
        })

    }

    loop {
        tokio::select! {
            event = mqtt_client.poll() => match event {
                Ok(event) => {
                    last_error = None;
                    mqtt_client.process_event(event)
                },
                Err(e) => {
                    if let None = last_error {
                        println!("Error = {:?}", e);
                        last_error = Some(e);
                    }
                }
            },
            Some(result) = futures.next() => {
                println!("Future's result arrived... {:?}", result)
            },
            _ = signal::ctrl_c() => break
        }
    }

    println!("Broke out of loop - finishing...");
}
