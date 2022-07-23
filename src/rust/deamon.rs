use clap::{Arg, App};

use std::fs;
use std::path::PathBuf;
use std::process;


mod mqtt_client;
use mqtt_client::MQTTClient;


use tokio::signal;



fn pyros_test_topic(msg: rumqttc::Publish, _mqtt_client: &MQTTClient) -> () {
    println!("Received message on {:?}: {:?}", msg.topic, msg.payload)
}


#[tokio::main(flavor = "current_thread")]
async fn main() {

    let exec_name = std::env::current_exe();

    let argument_parser = App::new(exec_name.unwrap().file_name().unwrap().to_str().unwrap())
        .version("2.0.1")
        .author("Daniel Sendula")
        .about("Core deamon for PyROS")
        .arg(Arg::with_name("verbose")
                .short("v")
                .multiple(true)
                .help("Verbose output"))
        .arg(Arg::with_name("home-dir")
                .short("d")
                .long("home-dir")
                .takes_value(true)
                .help("sets working directory"))
        .arg(Arg::with_name("host")
                .short("h")
                .long("host-address")
                .takes_value(true)
                .help("mqtt host address"))
        .get_matches();

    let debug_level = argument_parser.occurrences_of("verbose");
    let home_dir_arg = argument_parser.value_of("home-dir").unwrap_or(".");
    let home_dir: PathBuf = match fs::canonicalize(PathBuf::from(home_dir_arg)) {
        Ok(p) => p,
        Err(..) => {
            eprintln!("Supplied homedir {} does not exist", home_dir_arg);
            process::exit(1);
        }
    };
    let host_address = argument_parser.value_of("host").unwrap_or("127.0.0.1");

    println!("Verbosity level set to {}", debug_level);
    println!("Home dir is {}", &home_dir.display());
    println!("MQTT broker is {}", &host_address);

//    let (shutdown_send, shutdown_recv) = mpsc::unbounded_channel();

    let mut mqtt_client = MQTTClient::new(host_address);

    println!("Running process notification thread, too...");

    mqtt_client.subscribe("hello", pyros_test_topic).await;

    loop {
        tokio::select! {
            event = mqtt_client.eventloop.poll() => match event {
                Ok(event) => mqtt_client.process_event(event),
                Err(e) => {
                    println!("Error = {:?}", e);
                }
            },
            _ = signal::ctrl_c() => break
        }
    }

    println!("Broke out of loop - finishing...");
}
