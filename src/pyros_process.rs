use futures::stream::FuturesUnordered;
use std::io::Error;
use std::process::Stdio;
use futures::future::BoxFuture;
use tokio::process::{Child, Command};
use tokio::io::{BufReader, AsyncBufReadExt};



pub struct PyrosProcess {
    child_process: Child,
    // stdout_reader: Lines<BufReader<ChildStdout>>
}


impl PyrosProcess {
    pub fn new(command_to_run: &str, process_stdout_comms_futures:  &FuturesUnordered<BoxFuture<Result<(), std::io::Error>>>) -> PyrosProcess {
        let mut child = Command::new(command_to_run)
            // .args(&args)
            .stdout(Stdio::piped())
            .spawn()
            .unwrap();

        let stdout = child.stdout.take().expect("child did not have a handle to stdout");
        let mut stdout_reader = BufReader::new(stdout).lines();

        process_stdout_comms_futures.push(Box::pin(async move {
            while let Some(line) = stdout_reader.next_line().await? {
                println!("Stdout line: {}", line);
            }
            Ok::<(), Error>(())
        }));

        let process = PyrosProcess {
            child_process: child,
            // stdout_reader,
        };
        process
    }
}
