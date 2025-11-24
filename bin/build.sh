#!/bin/bash

LAAWS_BUILD_DIR="$(realpath "$1")"

LOCKSS_REST_SERVICES=(
  laaws-repository-service
  laaws-configservice
  laaws-poller
  laaws-crawler-service
  laaws-metadataservice
)

if [ -z "${LAAWS_BUILD_DIR}" ]; then
  echo "Please specify the path to the laaws-build directory"
  exit 1
fi

for lockss_svc in "${LOCKSS_REST_SERVICES[@]}"; do
  PROJECT_DIR="${LAAWS_BUILD_DIR}/${lockss_svc}"
  PYTHON_CLIENT_SRC="${PROJECT_DIR}/target/swagger_codegen_python"

  # Invoke Swagger codegen plugin in Maven to generate Python clients
  ( cd  ${PROJECT_DIR} && mvn generate-sources -DskipSwagger=true -DskipSwaggerPython=false )

  # Aggregate Python client sources into this src/ tree
  rsync -a -v ${PYTHON_CLIENT_SRC}/lockss/ src/lockss/

  # Add Swagger spec as resource
  PROJECT_CODE="$(cd "${PYTHON_CLIENT_SRC}/lockss/pyclient/"* && basename $(pwd))"
  SWAGGER="${PROJECT_DIR}/src/main/resources/swagger/swagger.yaml"
  cp -v "${SWAGGER}" "src/lockss/pyclient/${PROJECT_CODE}/"
done
