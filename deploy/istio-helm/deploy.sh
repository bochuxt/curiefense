#!/bin/bash


if [ -z "$DOCKER_TAG" ]; then
    if ! GITTAG="$(git describe --tag --long --exact-match 2> /dev/null)"; then
        GITTAG="$(git describe --tag --long --dirty)"
        echo "This commit is not tagged; use this for testing only"
    fi
    DOCKER_DIR_HASH="$(git rev-parse --short=12 HEAD:curiefense)"
    DOCKER_TAG="$GITTAG-$DOCKER_DIR_HASH"
fi

if ! kubectl api-resources|grep -q config.istio.io; then
    for i in crds/crd-*yaml; do kubectl apply -f "$i"; done
    echo "CRDs created, waiting 5s for them to be registered..."
    sleep 5
fi

helm upgrade --install --namespace istio-system --reuse-values --debug \
    -f chart/custom/enable-waf-ingress.yaml \
    --set "global.proxy.gw_image=curiefense/curieproxy-istio:$DOCKER_TAG" \
    --set "global.proxy.curiesync_image=curiefense/curiesync:$DOCKER_TAG" \
    istio-cf chart/
