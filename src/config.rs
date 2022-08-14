use clap::Parser;

use std::collections::HashMap;
use std::error;
use std::fs::File;
use std::io::BufReader;
use std::path::{Path, PathBuf};

use java_properties::{PropertiesIter};


#[derive(Parser)]
// #[derive(Parser, Debug)]
#[clap(name = "PyROS")]
#[clap(author = "Daniel Sendula")]
#[clap(version = "2.0.1")]
#[clap(about = "Core deamon for PyROS", long_about = None)]
pub struct PyrosCliArgs {
    #[clap(short = 'd', long = "home-dir", value_parser)]
    pub home_dir: Option<String>,

    #[clap(short = 'c', long, value_parser)]
    pub command: Option<String>,

    #[clap(short = 'h', long = "mqtt-host", value_parser)]
    mqtt_host: Option<String>,

    #[clap(short = 'm', long = "mqtt-port", value_parser)]
    mqtt_port: Option<String>,

    #[clap(short = 'v', long, action = clap::ArgAction::Count)]
    verbose: u8,
}


pub struct Config {
    pub home_dir: PathBuf,
    config_file: PathBuf,
    pub verbosity: u8,
    pub mqtt_host: String,
    pub mqtt_port: u16,
    pub mqtt_timeout: i32,
    pub mqtt_max_reconnect_retries: i32,
    pub thread_kill_timeout: i32,
    pub agents_check_timeout: i32,
    pub agents_kill_timeout: i32,
}


impl Config {
    pub fn new(home_dir: &Path, args: PyrosCliArgs) -> Config {
        let config_file = home_dir.join("pyros.config");

        let mut config_map: HashMap<String, String> = HashMap::new();
        config_map.insert("debug_level".to_string(), args.verbose.to_string().to_owned());

        if args.mqtt_host.is_some() {
            config_map.insert("mqtt.host".to_string(), args.mqtt_host.unwrap().to_owned());
        }
        if args.mqtt_port.is_some() {
            config_map.insert("mqtt.port".to_string(), args.mqtt_port.unwrap());
        }

        let mut config = Config {
            home_dir: home_dir.to_path_buf(),
            config_file,
            verbosity: 0,
            mqtt_host: String::from("localhost"),
            mqtt_port: 1883,
            mqtt_timeout: 60,
            mqtt_max_reconnect_retries: 20,
            thread_kill_timeout: 1,
            agents_check_timeout: 1,
            agents_kill_timeout: 180,
        };

        config.load_from_config_internal(config_map);

        config
    }

    pub fn load_from_config_file(mut self){
        self.load_from_config_internal(HashMap::new());
    }

    fn load_from_config_internal(&mut self, config_map: HashMap<String, String>){
        let config_map = Config::load_config(&self.config_file, config_map)
            .expect(format!("Cannot read config file {:?}", &self.config_file).as_ref());

        for (key, val) in config_map {
            match &key[..] {
                "debug_level" => {
                    let debug_level = val;
                    self.verbosity = debug_level.parse::<u8>()
                        .expect(format!("Cannot parse debug.level - not an iteger '{:?}'", debug_level).as_ref());
                },
                "mqtt.host" => self.mqtt_host = val,
                "mqtt.port" => {
                    let port = val;

                    self.mqtt_port = port.parse::<u16>()
                        .expect(format!("Cannot parse mqtt.port - not an iteger '{:?}'", port).as_ref());
                },
                key => {
                    println!("Unknown property found {}", key)
                }
            }
        }
    }

    fn load_config<P: AsRef<Path>>(filename: P, mut config: HashMap<String, String>) -> Result<HashMap<String, String>, Box<dyn error::Error>> {
        if filename.as_ref().exists() {
            let mut p = PropertiesIter::new(BufReader::new(File::open(filename)?));
            p.read_into(|k, v| {
              config.insert(k, v);
            })?;
            Ok(config)
        } else {
            Ok(config)
        }
    }
}



