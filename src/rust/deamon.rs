use clap::{Arg, App};
// use std::env;
use std::fs;
use std::path::PathBuf;
use std::process;
// use std::thread;

mod mqtt_client;
use mqtt_client::MQTTClient;

//use crossbeam_channel::{select, Sender};
//use crossbeam_channel::{select};


fn pyros_test_topic(msg: rumqttc::Publish, _mqtt_client: &MQTTClient) -> () {
    println!("Received message on {:?}: {:?}", msg.topic, msg.payload)
}


fn main() {

    let exec_name = std::env::current_exe(); //.unwrap().file_name().unwrap().to_str().unwrap();

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

    println!("Verbosity level set to {}", debug_level);
    println!("Home dir is {}", &home_dir.display());


    let mut mqtt_client = MQTTClient::new("127.0.0.1");
    let (stop_sender, _stop_receiver) = crossbeam_channel::bounded(1);
//    let process_thread = thread::spawn(move || mqtt_client.process_notifications(stop_receiver));
//
    ctrlc::set_handler(move || {
        let _ = stop_sender.send(true);
    }).expect("Error setting Ctrl-C handler");

    println!("Running process notification thread, too...");
    
    
    mqtt_client.subscribe("pyros-test", pyros_test_topic);
    
//    loop {
//        select! {
//            recv(mqtt_client.notifications) -> notification => {
//                println!("Received {:?}", notification);
//                match notification {
//                    Ok(notification) => mqtt_client.process(notification),
//                    _ => {}
//                }
//            }
//            recv(stop_receiver) -> _done => break
//        }
//    }
//
//    let mut connection = mqtt_client.connection;
//
//    for (i, notification) in connection.iter().enumerate() {
//        match notification {
//            Ok(event) => mqtt_client.process(event),
//            Err(e) => {
//                println!("Error = {:?}", e);
//            }
//        }
//    }
//

    mqtt_client.process_loop();
}
