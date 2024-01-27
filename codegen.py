#!/usr/bin/env python3

import yaml
import requests
import tempfile
import subprocess


def pascal_to_snake(s):
    return "".join(["_" + c.lower() if c.isupper() else c for c in s]).lstrip("_")


rust_lib = """//! Kubernetes CRDs for the Gateway API
//!
//! This library provides automatically generated types for the [Kubernetes Gateway API CRDs]. It is
//! intended to be used with the [Kube-rs] library.
//!
//! [Kubernetes Gateway API CRDs]: https://github.com/kubernetes-sigs/gateway-api/tree/main/config/crd/standard
//! [Kube-rs]: https://kube.rs/

"""

crds = []
crd_sources = [
    "https://raw.githubusercontent.com/kubernetes-sigs/gateway-api/v1.0.0/config/crd/standard/gateway.networking.k8s.io_gatewayclasses.yaml",
    "https://raw.githubusercontent.com/kubernetes-sigs/gateway-api/v1.0.0/config/crd/standard/gateway.networking.k8s.io_gateways.yaml",
    "https://raw.githubusercontent.com/kubernetes-sigs/gateway-api/v1.0.0/config/crd/standard/gateway.networking.k8s.io_httproutes.yaml",
    "https://raw.githubusercontent.com/kubernetes-sigs/gateway-api/v1.0.0/config/crd/standard/gateway.networking.k8s.io_referencegrants.yaml",
]

not_defaulted = [
    "GatewayClassStatusConditions",
    "GatewayStatusConditions",
    "HTTPRouteRulesBackendRefsFiltersUrlRewritePath",
    "HTTPRouteRulesFilters",
    "HTTPRouteRulesBackendRefsFiltersRequestRedirectPath",
    "GatewayStatusListenersConditions",
    "HTTPRouteRulesFiltersRequestRedirectPath",
    "HTTPRouteRulesBackendRefsFilters",
    "HTTPRouteRulesFiltersUrlRewritePath",
    "HTTPRouteStatusParentsConditions",
]

for source in crd_sources:
    crds.append(yaml.safe_load(requests.get(source).text))

for crd in crds:
    file_name = crd["metadata"]["name"].removesuffix(".gateway.networking.k8s.io")
    rust_code = ""
    # Save the CRD as a tmp yaml file
    with tempfile.NamedTemporaryFile(mode="w") as f:
        yaml.dump(crd, f)
        tmp_file = f.name
        rust_code = subprocess.run(
            ["kopium", "-f", tmp_file, "--schema=derived", "--docs", "-b"],
            capture_output=True,
        )
        if rust_code.returncode != 0:
            print(rust_code.stderr.decode("utf-8"))
            exit(1)
        rust_code = rust_code.stdout.decode("utf-8")

    rust_code = rust_code.replace(
        f"// kopium command: kopium -f {tmp_file} --schema=derived --docs -b",
        f"// kopium command: kopium -f {file_name}.yml --schema=derived --docs -b",
    )
    rust_code = "\n".join(
        [
            line.replace("#[builder(", '#[cfg_attr(feature = "builder", builder(')
            .strip()
            .removesuffix("]")
            + ")]"
            if "#[builder(" in line
            else line
            for line in rust_code.split("\n")
        ]
    )
    # We're not setting PartialEq, Hash, Default with kopium because then rustfmt would insert a line break, which would make this script more complicated
    rust_code = (
        rust_code.replace(
            ", TypedBuilder, JsonSchema)]\npub struct",
            ", PartialEq, Default, TypedBuilder, JsonSchema)]\npub struct",
        )
        .replace(
            ", TypedBuilder, JsonSchema)]\n#[kube",
            ", PartialEq, Default, TypedBuilder, JsonSchema)]\n#[kube",
        )
        .replace(
            ", TypedBuilder, JsonSchema)]\npub enum",
            ", PartialEq, TypedBuilder, JsonSchema)]\npub enum",
        )
    )
    for not_defaulted_field in not_defaulted:
        rust_code = rust_code.replace(
            f"Default, TypedBuilder, JsonSchema)]\npub struct {not_defaulted_field}",
            f"TypedBuilder, JsonSchema)]\npub struct {not_defaulted_field}",
        )
    rust_code = "\n".join(
        [
            line.replace(
                ", TypedBuilder, JsonSchema)]",
                ')]\n#[cfg_attr(feature = "builder", derive(TypedBuilder))]\n#[cfg_attr(feature = "schemars", derive(JsonSchema))]\n#[cfg_attr(not(feature = "schemars"), kube(schema="disabled"))]',
            )
            if line.startswith("#[derive(") and "CustomResource" in line
            else line.replace(
                ", TypedBuilder, JsonSchema)]",
                ')]\n#[cfg_attr(feature = "builder", derive(TypedBuilder))]\n#[cfg_attr(feature = "schemars", derive(JsonSchema))]',
            )
            if line.startswith("#[derive(")
            else line
            for line in rust_code.split("\n")
        ]
    )
    rust_code = (
        rust_code.replace(
            "use typed_builder::TypedBuilder;",
            '#[cfg(feature = "builder")]\nuse typed_builder::TypedBuilder;',
        )
        .replace(
            "use schemars::JsonSchema;",
            '#[cfg(feature = "schemars")]\nuse schemars::JsonSchema;',
        )
        .replace("use kube::CustomResource;", "use kube_derive::CustomResource;")
        .replace(
            '#[cfg_attr(feature = "builder", derive(TypedBuilder))]\n#[cfg_attr(feature = "schemars", derive(JsonSchema))]\npub enum',
            '#[cfg_attr(feature = "schemars", derive(JsonSchema))]\npub enum',
        )
    )
    rust_file = f"./src/{file_name}.rs"
    with open(rust_file, "w") as f:
        f.write(rust_code)
    # Format the code
    subprocess.run(["rustfmt", rust_file])
    rust_lib += f"pub mod {file_name};\npub use {file_name}::*;\n"

with open("./src/lib.rs", "w") as f:
    f.write(rust_lib)
