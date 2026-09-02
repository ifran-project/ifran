#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
workspace="${OSC_BUILD_WORKSPACE:-$script_dir/.build}"
output_dir="${OSC_BUILD_OUTPUT:-$script_dir/artifacts}"
image_prefix="${OSC_IMAGE_PREFIX:-docker.io/r2labuser}"
platform="${OSC_BUILD_PLATFORM:-linux/amd64}"
save_images="${OSC_SAVE_IMAGES:-false}"

image_prefix="${image_prefix%/}"

components=(builder-ubuntu builder-alpine appmgr appmgr-g-helm appmgr-m-helm dbaas e2term e2mgr rtmgr submgr a1mediator xapp-onboarder xapp-onboarder-helm3)

usage() {
  echo "usage: $0 <component|all|list> [--push]" >&2
  echo "components: ${components[*]}" >&2
}

component="${1:-}"
push=false
if [[ "${2:-}" == "--push" ]]; then
  push=true
elif [[ -n "${2:-}" ]]; then
  usage
  exit 2
fi

if [[ "$component" == "list" ]]; then
  printf '%s\n' "${components[@]}"
  exit 0
fi

if [[ "$component" == "all" ]]; then
  selected=("${components[@]}")
elif [[ " ${components[*]} " == *" $component "* ]]; then
  case "$component" in
    appmgr|e2term|e2mgr|rtmgr|submgr) selected=(builder-ubuntu "$component") ;;
    dbaas) selected=(builder-alpine "$component") ;;
    *) selected=("$component") ;;
  esac
else
  usage
  exit 2
fi

repository_for() {
  case "$1" in
    builder-ubuntu|builder-alpine) echo "https://github.com/o-ran-sc/it-dev.git" ;;
    appmgr|xapp-onboarder) echo "https://github.com/o-ran-sc/ric-plt-appmgr.git" ;;
    dbaas) echo "https://github.com/o-ran-sc/ric-plt-dbaas.git" ;;
    e2term) echo "https://github.com/o-ran-sc/ric-plt-e2.git" ;;
    e2mgr) echo "https://github.com/o-ran-sc/ric-plt-e2mgr.git" ;;
    rtmgr) echo "https://github.com/o-ran-sc/ric-plt-rtmgr.git" ;;
    submgr) echo "https://github.com/o-ran-sc/ric-plt-submgr.git" ;;
    a1mediator) echo "https://github.com/o-ran-sc/ric-plt-a1.git" ;;
  esac
}

commit_for() {
  case "$1" in
    builder-ubuntu) echo "913dfd67162776f82670cd6d39fb42d72fccdc97" ;;
    builder-alpine) echo "45ee411da14af02b02aedcd70640847bf93e9d9a" ;;
    appmgr|xapp-onboarder) echo "2f70f24239e3f9281b899b7d5b4807cf36e062d1" ;;
    dbaas) echo "23c983c62fa8f1677351ced9fbfe65c64375edb9" ;;
    e2term) echo "6f2315b1a63e224c25c1a7202160e75d47d8bcdf" ;;
    e2mgr) echo "e53b21660c881f07e93d153048181eee1b391fbb" ;;
    rtmgr) echo "c794f21a206c6cab2e352128201333a5924aee61" ;;
    submgr) echo "708224f4ffcbfc5d79709ed175d2f271053c111b" ;;
    a1mediator) echo "09a757b4fd63198d8690d50b52bfd04552d47f1f" ;;
  esac
}

source_name_for() {
  case "$1" in
    builder-ubuntu|builder-alpine) echo "it-dev" ;;
    appmgr|xapp-onboarder) echo "ric-plt-appmgr" ;;
    dbaas) echo "ric-plt-dbaas" ;;
    e2term) echo "ric-plt-e2" ;;
    e2mgr) echo "ric-plt-e2mgr" ;;
    rtmgr) echo "ric-plt-rtmgr" ;;
    submgr) echo "ric-plt-submgr" ;;
    a1mediator) echo "ric-plt-a1" ;;
  esac
}

image_name_for() {
  case "$1" in
    builder-ubuntu) echo "bldr-ubuntu22-c-go:1.0.0" ;;
    builder-alpine) echo "bldr-alpine3-go:2.0.0" ;;
    appmgr) echo "ric-plt-appmgr:0.5.9" ;;
    appmgr-g-helm) echo "ric-plt-appmgr:0.5.7-helm3" ;;
    appmgr-m-helm) echo "ric-plt-appmgr:0.5.9-helm3" ;;
    dbaas) echo "ric-plt-dbaas:0.6.5" ;;
    e2term) echo "ric-plt-e2:6.0.8" ;;
    e2mgr) echo "ric-plt-e2mgr:6.0.8" ;;
    rtmgr) echo "ric-plt-rtmgr:0.9.7" ;;
    submgr) echo "ric-plt-submgr:0.10.4" ;;
    a1mediator) echo "ric-plt-a1:3.2.3" ;;
    xapp-onboarder) echo "xapp-onboarder:1.0.8" ;;
    xapp-onboarder-helm3) echo "xapp-onboarder:1.0.8-helm3" ;;
  esac
}

dockerfile_for() {
  case "$1" in
    builder-ubuntu) echo "bldr-imgs/bldr-ubuntu22-c-go/Dockerfile" ;;
    builder-alpine) echo "bldr-imgs/bldr-alpine3-go/Dockerfile" ;;
    appmgr) echo "Dockerfile" ;;
    appmgr-g-helm) echo "appmgr-g-helm.Dockerfile" ;;
    appmgr-m-helm) echo "appmgr-m-helm.Dockerfile" ;;
    dbaas) echo "docker/Dockerfile.redis" ;;
    e2term) echo "RIC-E2-TERMINATION/Dockerfile" ;;
    e2mgr) echo "E2Manager/Dockerfile" ;;
    rtmgr|submgr|a1mediator) echo "Dockerfile" ;;
    xapp-onboarder) echo "xapp_orchestrater/dev/ci/xapp_onboarder/Dockerfile" ;;
    xapp-onboarder-helm3) echo "xapp-onboarder-helm3.Dockerfile" ;;
  esac
}

context_for() {
  case "$1" in
    builder-ubuntu) echo "bldr-imgs/bldr-ubuntu22-c-go" ;;
    builder-alpine) echo "bldr-imgs/bldr-alpine3-go" ;;
    e2term) echo "RIC-E2-TERMINATION" ;;
    e2mgr) echo "E2Manager" ;;
    xapp-onboarder) echo "xapp_orchestrater/dev" ;;
    *) echo "." ;;
  esac
}

prepare_dockerfile() {
  local component_name="$1"
  local source_dockerfile="$2"
  local generated_dir="$workspace/.dockerfiles"
  local generated_dockerfile="$generated_dir/$component_name.Dockerfile"

  mkdir -p "$generated_dir"
  sed \
    -e 's|nexus3.o-ran-sc.org:10001/ubuntu:22.04|ubuntu:22.04|g' \
    -e "s|nexus3.o-ran-sc.org:10002/o-ran-sc/bldr-ubuntu22-c-go:1.0.0|$image_prefix/bldr-ubuntu22-c-go:1.0.0|g" \
    -e "s|nexus3.o-ran-sc.org:10002/o-ran-sc/bldr-alpine3-go:2.0.0|$image_prefix/bldr-alpine3-go:2.0.0|g" \
    -e 's|https://storage.googleapis.com/kubernetes-helm/|https://get.helm.sh/|g' \
    "$source_dockerfile" > "$generated_dockerfile"
  echo "$generated_dockerfile"
}

fetch_source() {
  local component_name="$1"
  local source_name repository commit source_dir

  if [[ "$component_name" == "appmgr-g-helm" || "$component_name" == "appmgr-m-helm" || "$component_name" == "xapp-onboarder-helm3" ]]; then
    echo "$script_dir/overlays"
    return
  fi

  source_name="$(source_name_for "$component_name")"
  repository="$(repository_for "$component_name")"
  commit="$(commit_for "$component_name")"
  source_dir="$workspace/$source_name"

  if [[ ! -d "$source_dir/.git" ]]; then
    git init "$source_dir" >&2
    git -C "$source_dir" remote add origin "$repository"
  fi

  if ! git -C "$source_dir" cat-file -e "${commit}^{commit}" 2>/dev/null; then
    git -C "$source_dir" fetch --depth 1 origin "$commit"
  fi
  git -C "$source_dir" checkout --detach "$commit"

  echo "$source_dir"
}

build_component() {
  local component_name="$1"
  local source_dir dockerfile context image archive
  local -a build_options=()
  source_dir="$(fetch_source "$component_name")"
  dockerfile="$(prepare_dockerfile "$component_name" "$source_dir/$(dockerfile_for "$component_name")")"
  context="$source_dir/$(context_for "$component_name")"
  image="$image_prefix/$(image_name_for "$component_name")"
  archive="$output_dir/${component_name}-$(image_name_for "$component_name" | tr ':/' '-')-amd64.tar"

  echo "building $component_name as $image"
  docker build \
    "${build_options[@]}" \
    --platform "$platform" \
    --file "$dockerfile" \
    --tag "$image" \
    "$context"

  docker image inspect "$image" --format '{{.Id}}'

  if [[ "$save_images" == "true" ]]; then
    docker save --output "$archive" "$image"
    echo "archive $archive"
  fi

  if [[ "$push" == "true" ]]; then
    docker push "$image"
  fi
}

mkdir -p "$workspace" "$output_dir"

for selected_component in "${selected[@]}"; do
  build_component "$selected_component"
done

echo "completed ${selected[*]}"
if [[ "$push" != "true" ]]; then
  echo "images were not pushed; rerun with --push after docker login"
fi
