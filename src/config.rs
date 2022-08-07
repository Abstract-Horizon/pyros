use std::collections::HashMap;
use std::error;
use std::fs::File;
use std::io::BufReader;
use std::path::Path;

use java_properties::{PropertiesIter};


pub fn load_config<P: AsRef<Path>>(filename: P, mut config: HashMap<String, String>) -> Result<HashMap<String, String>, Box<dyn error::Error>> {
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
