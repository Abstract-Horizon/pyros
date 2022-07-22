use std::collections::HashMap;
// use std::process;
// use std::thread;

use rumqttc::{AsyncClient, EventLoop, MqttOptions, QoS, Event, Incoming};

//use mqtt311;

// use crossbeam_channel::{select, Sender, Receiver};
// use crossbeam_channel::{select};
use std::time::Duration;



pub struct MQTTClient {
    mqtt_client: AsyncClient,
    eventloop: EventLoop,
    subscriptions: HashMap<&'static str, fn(msg: rumqttc::Publish, mqtt_client: &MQTTClient)>,
}

impl MQTTClient {
    pub fn new(address: &str) -> MQTTClient {
        let mut mqttoptions = MqttOptions::new("rumqtt-sync", address, 1883);
        mqttoptions.set_keep_alive(Duration::from_secs(5));

        let (mqtt_client, eventloop) = AsyncClient::new(mqttoptions, 10);
        println!("Connected to {}", address);

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

    pub async fn subscribe_storage(&mut self, topic: &'static str, callback: fn(msg: rumqttc::Publish, mqtt_client: &MQTTClient) -> ()) {
        self.mqtt_client.subscribe(&("storage/write/".to_string() + topic), QoS::AtMostOnce).await.unwrap();
        let _ = self.mqtt_client.publish(&("storage/read/".to_string() + topic), QoS::AtLeastOnce, false, "");
        self.subscriptions.insert(Box::leak(("storage/write/".to_string() + topic).into_boxed_str()), callback);
    }

//    pub fn process(&mut self, notification: Event) {
//        match notification {
//            Event::Publish(msg) => {
//                match self.subscriptions.get(&msg.topic_name.as_str()) {
//                    Some(f) => f(msg, self),
//                    _ => println!("Cannot find notification for topic {}", msg.topic_name)
//                }
//            },
//            Event::Reconnection => {
//                for key in self.subscriptions.keys() {
//                    let topic : &'static str = key;
//                    let _ = self.mqtt_client.subscribe(topic, QoS::AtMostOnce);
//                }
//            },
//            _ => { }
//        }
//    }

    pub async fn process_loop(&mut self) {
        loop {
            match self.eventloop.poll().await {
                Ok(event) => self.process(event),
                Err(e) => {
                    println!("Error = {:?}", e);
                }
            }
        }
    }

    pub fn process(&self, event: Event) {
        match event {
            Event::Incoming(Incoming::Publish(p)) => {
                match self.subscriptions.get(&p.topic.as_str()) {
                    Some(f) => f(p, &self),
                    _ => println!("Cannot find notification for topic {}", p.topic)
                }
            },
            Event::Incoming(i) => {
                println!("Incoming = {:?}", i);
            }
            Event::Outgoing(o) => println!("Outgoing = {:?}", o),
            _ => {}
        }
    }
}
