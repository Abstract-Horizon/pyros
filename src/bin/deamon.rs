// use clap::{Arg, App};
use clap::Parser;

use std::fs;
use std::path::PathBuf;
use std::process;
use std::process::{Command, Stdio};
use rumqttc::ConnectionError;
use tokio::io::BufReader;

use pyros::mqtt_client::MQTTClient;

use tokio::signal;



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
    #[clap(short = 'd', long, value_parser)]
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
    let home_dir: PathBuf = match fs::canonicalize(PathBuf::from(home_dir_arg)) {
        Ok(p) => p,
        Err(..) => {
            eprintln!("Supplied homedir {} does not exist", home_dir_arg);
            process::exit(1);
        }
    };

    let host_address = args.host.as_deref().unwrap_or("127.0.0.1");

    println!("Verbosity level set to {}", args.verbose);
    println!("Home dir is {}", &home_dir.display());
    println!("MQTT broker is {}", &host_address);

    let mut mqtt_client = MQTTClient::new(host_address);

    println!("Running process notification thread, too...");

    mqtt_client.subscribe("hello", pyros_test_topic).await;

    let mut last_error: Option<ConnectionError> = None;

    // let mut cmd = Command::new(binary.as_ref())
    //     .args(&args)
    //     .stdout(Stdio::piped())
    //     .spawn()
    //     .unwrap();
    //
    // let stdout = cmd.stdout.as_mut().unwrap();
    // let stdout_reader = BufReader::new(stdout);
    // let stdout_lines = stdout_reader.lines();

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
            _ = signal::ctrl_c() => break
        }
    }

    println!("Broke out of loop - finishing...");
}
