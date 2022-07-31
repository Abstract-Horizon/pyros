use std::collections::HashMap;
use std::time::Duration;

use rumqttc::{AsyncClient, EventLoop, MqttOptions, QoS, Event, Incoming, ConnectionError};

use rand::{thread_rng, Rng};
use rand::distributions::Alphanumeric;


pub struct MQTTClient {
    mqtt_client: AsyncClient,
    eventloop: EventLoop,
    subscriptions: HashMap<&'static str, fn(msg: rumqttc::Publish, mqtt_client: &MQTTClient)>,
}

impl MQTTClient {
    pub fn new(address: &str) -> MQTTClient {
        let random_part = random_string(5);
        let mut mqttoptions = MqttOptions::new("pyros_".to_owned() + &random_part, address, 1883);
        mqttoptions.set_keep_alive(Duration::from_secs(5));

        let (mqtt_client, eventloop) = AsyncClient::new(mqttoptions, 10);
        println!("Connected to {} as {}", address, "pyros_".to_owned() + &random_part);

        MQTTClient {
            mqtt_client,
            eventloop,
            subscriptions: HashMap::new()
        }
    }

    pub async fn subscribe(&mut self, topic: &'static str, callback: fn(msg: rumqttc::Publish, mqtt_client: &MQTTClient) -> ()) {
        self.mqtt_client.subscribe(topic, QoS::AtMostOnce).await.unwrap();
        self.subscriptions.insert(topic, callback);
    }

//    pub async fn subscribe_storage(&mut self, topic: &'static str, callback: fn(msg: rumqttc::Publish, mqtt_client: &MQTTClient) -> ()) {
//        self.mqtt_client.subscribe(&("storage/write/".to_string() + topic), QoS::AtMostOnce).await.unwrap();
//        let _ = self.mqtt_client.publish(&("storage/read/".to_string() + topic), QoS::AtLeastOnce, false, "");
//        self.subscriptions.insert(Box::leak(("storage/write/".to_string() + topic).into_boxed_str()), callback);
//    }

//    pub async fn process_loop(&mut self) {
//        match self.eventloop.poll().await {
//            Ok(event) => self.process_event(event),
//            Err(e) => {
//                println!("Error = {:?}", e);
//            }
//        }
//    }

    pub fn process_event(&self, event: Event) {
        match event {
            Event::Incoming(Incoming::Publish(p)) => {
                match self.subscriptions.get(&p.topic.as_str()) {
                    Some(f) => f(p, &self),
                    _ => println!("Cannot find notification for topic {}", p.topic)
                }
            },
            // Event::Incoming(i) => println!("Incoming = {:?}", i),
            // Event::Outgoing(o) => println!("Outgoing = {:?}", o),
            _ => {}
        }
    }

    pub async fn poll(&mut self) -> Result<Event, ConnectionError> {
        self.eventloop.poll().await
    }
}

fn random_string(n: usize) -> String {
    thread_rng()
        .sample_iter(&Alphanumeric)
        .take(n)
        .map(char::from)
        .collect()
}

