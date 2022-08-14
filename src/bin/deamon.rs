// use clap::{Arg, App};
use clap::Parser;

use std::fs;
use std::io::Error;
use std::path::Path;
use std::process;
use std::process::{Stdio};

use futures::stream::{FuturesUnordered, StreamExt};

use tokio::{io::{BufReader, AsyncBufReadExt}, process::Command};

use tokio::signal;

use rumqttc::ConnectionError;
use pyros::config::{Config, PyrosCliArgs};

use pyros::mqtt_client::MQTTClient;


fn pyros_test_topic(msg: rumqttc::Publish, _mqtt_client: &MQTTClient) -> () {
    println!("Received message on {:?}: {:?}", msg.topic, msg.payload)
}

#[tokio::main(flavor = "current_thread")]
async fn main() {

    let args = PyrosCliArgs::parse();

    let args_commnad = args.command.to_owned();
    let home_dir_arg = args.home_dir.as_deref().unwrap_or(".");
    let home_dir = match fs::canonicalize(Path::new(home_dir_arg)) {
        Ok(p) => p,
        Err(..) => {
            eprintln!("Supplied homedir {} does not exist", home_dir_arg);
            process::exit(1);
        }
    };
    println!("Home dir is {}", &home_dir.display());

    let config = Config::new(&home_dir, args);

    println!("Verbosity level set to {}", config.verbosity);
    println!("MQTT broker is {}", config.mqtt_host);

    let mut mqtt_client = MQTTClient::new(config.mqtt_host.as_str());

    println!("Running process notification thread, too...");

    mqtt_client.subscribe("hello", pyros_test_topic).await;

    let mut last_error: Option<ConnectionError> = None;

    let mut process_stdout_comms_futures = FuturesUnordered::new();

    if let Some(command_to_run) = args_commnad {
        let mut child = Command::new(command_to_run)
            // .args(&args)
            .stdout(Stdio::piped())
            .spawn()
            .unwrap();

        let stdout = child.stdout.take().expect("child did not have a handle to stdout");

        let mut stdout_reader = BufReader::new(stdout).lines();
        process_stdout_comms_futures.push(async move {
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
            Some(result) = process_stdout_comms_futures.next() => {
                println!("Future's result arrived... {:?}", result)
            },
            _ = signal::ctrl_c() => break
        }
    }

    println!("Broke out of loop - finishing...");
}
