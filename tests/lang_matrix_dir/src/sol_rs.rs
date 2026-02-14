use std::io::{self, Read};

fn main() {
    let mut input = String::new();
    io::stdin().read_to_string(&mut input).unwrap();
    if let Ok(x) = input.trim().parse::<i32>() {
        println!("{}", x);
    }
}
