//! Explicit per-game inputs for local opponent experiments; absent for ordinary matches.
use anyhow::{bail, ensure, Context, Result};
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct TeamConfig { pub seed: u64, pub salt: u64, pub unmetered: bool }

pub fn parse(text: &str) -> Result<[Option<TeamConfig>; 2]> {
    let value: serde_json::Value = serde_json::from_str(text)?;
    let obj = value.as_object().context("runtime config must be an object")?;
    ensure!(obj.len() == 2 && obj.contains_key("a") && obj.contains_key("b"), "runtime config requires exactly a and b");
    let mut out = [None, None];
    for (i, key) in ["a", "b"].iter().enumerate() {
        let v = &obj[*key];
        if v.is_null() { continue; }
        let o = v.as_object().context("team config must be an object or null")?;
        ensure!(o.len() == 3, "team config requires seed, salt, unmetered only");
        out[i] = Some(TeamConfig { seed: o.get("seed").and_then(|v| v.as_u64()).context("seed must be uint64")?,
            salt: o.get("salt").and_then(|v| v.as_u64()).context("salt must be uint64")?,
            unmetered: o.get("unmetered").and_then(|v| v.as_bool()).context("unmetered must be boolean")? });
    }
    if out.iter().filter(|x| x.is_some()).count() != 1 { bail!("configure exactly one opponent team per match"); }
    Ok(out)
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test] fn side_swap_and_rejection() {
        let c = r#"{"a":null,"b":{"seed":18446744073709551615,"salt":7,"unmetered":true}}"#;
        let x=parse(c).unwrap(); assert_eq!(x[0],None); assert_eq!(x[1].unwrap().seed,u64::MAX);
        for bad in [r#"{"a":null,"b":null}"#, r#"{"a":null,"b":{"seed":-1,"salt":2,"unmetered":true}}"#,
            r#"{"a":{},"b":null}"#] { assert!(parse(bad).is_err()); }
        let y=parse(r#"{"b":null,"a":{"seed":9,"salt":7,"unmetered":false}}"#).unwrap();
        assert_eq!(y[0].unwrap().seed,9); assert_eq!(y[1],None);
    }
}
