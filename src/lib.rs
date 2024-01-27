//! Kubernetes CRDs for the Gateway API
//!
//! This library provides automatically generated types for the [Kubernetes Gateway API CRDs]. It is
//! intended to be used with the [Kube-rs] library.
//!
//! [Kubernetes Gateway API CRDs]: https://github.com/kubernetes-sigs/gateway-api/tree/main/config/crd/standard
//! [Kube-rs]: https://kube.rs/

pub mod gatewayclasses;
pub use gatewayclasses::*;
pub mod gateways;
pub use gateways::*;
pub mod httproutes;
pub use httproutes::*;
pub mod referencegrants;
pub use referencegrants::*;
