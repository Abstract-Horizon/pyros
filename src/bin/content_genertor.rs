use std::time::Duration;

use rand::Rng;
use tokio::time::sleep;

const RESULT_LINES: &'static [&'static str] = &[
    "Optimising butterflies for their effect...",
    "Scanning for the black holes...",
    "Sorted memory access.",
    "Found anomaly - expliring it again:"
];


#[tokio::main(flavor = "current_thread")]
async fn main() {

    println!("Starting random content generator");

    let mut rng = rand::thread_rng();
    let mut line_number = 0;

    loop {
        sleep(Duration::from_millis(rng.gen_range(50..2001))).await;
        let selected_line = rng.gen_range(0..RESULT_LINES.len());
        println!("{}: {}", line_number, RESULT_LINES[selected_line]);
        line_number = line_number + 1;
    }
}
