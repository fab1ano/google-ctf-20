use async_std::net::{TcpListener, TcpStream};
use async_std::prelude::*;
use log::{debug, warn};
use pwn_tracing::bst::BinarySearchTree;
use uuid::Uuid;

const BIND_ADDR: &str = "0.0.0.0:1337";

async fn accept(mut stream: TcpStream, checks: Vec<Uuid>) -> std::io::Result<()> {
    debug!("Accepted connection");
    let bytes = (&stream).bytes().map(|b| b.unwrap());
    let chunks = {
        // Ugh, async_std::prelude::StreamExt doesn't have chunks(),
        // but it conflicts with futures::stream::StreamExt for the methods it
        // does have.
        use futures::stream::StreamExt;
        bytes.chunks(16)
    };

    let mut count: u32 = 0;
    let ids = chunks.filter_map(|bytes| {
        count += 1;
        Uuid::from_slice(&bytes).ok()
    });
    debug!("Waiting for IDs");
    let tree = { // This is a new bst into which our values will be inserted
        use futures::stream::StreamExt;
        ids.collect::<BinarySearchTree<_>>()
    }
    .await;
    debug!("Received {} IDs", count);
    stream.write_all(&count.to_be_bytes()).await?;

    debug!("Checking uploaded IDs for any matches");
    checks // This is coming from the command line
        .iter()
        .filter(|check| tree.contains(check))
        .for_each(|check| warn!("Uploaded IDs contain {}!", check));
    debug!("Done");
    stream.shutdown(std::net::Shutdown::Both)?;
    debug!("No error");
    Ok(())
}

#[async_std::main]
async fn main() -> std::io::Result<()> {
    env_logger::init();

    for argument in std::env::args().skip(1) {
        debug!("arg: {:?} ({:?})", argument.as_bytes(), Uuid::from_slice(argument.as_bytes()));
    }

    let checks: Vec<Uuid> = std::env::args()
        .skip(1)
        .map(|arg| Uuid::from_slice(arg.as_bytes()).unwrap())
        .collect();

    debug!("Loaded checks: {:?}", checks);

    let listener = TcpListener::bind(BIND_ADDR).await?;
    let mut incoming = listener.incoming();

    while let Some(stream) = incoming.next().await {
        debug!("Loaded checks: {:?}", checks);
        let stream = stream?;
        async_std::task::spawn(accept(stream, checks.clone()));
    }
    Ok(())
}
