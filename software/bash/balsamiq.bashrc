# b-ssh-jenkins-master() {
#   cat <<EOF
# Once logged to become Jenkins user do this:
#   $ sudo -s
#   # su jenkins

# Read more: https://balsamiq.atlassian.net/wiki/x/ToQuEw

# EOF
#   ssh ubuntu@ec2-46-137-119-50.eu-west-1.compute.amazonaws.com
# }

alias b-aws-production-products='envchain balsamiq-aws-llc aws'
alias b-aws-olio-production='envchain balsamiq-aws-srl aws'
alias b-aws-everything-else='envchain balsamiq-aws-srlinternal aws'

# TODO: remove hard-coded path
alias b-convox-production='envchain balsamiq-convox-production $HOME/Development/balsamiq/convox-ops/bin/convox-wrapper'
# alias b-convox-rtc-production='envchain balsamiq-convox-rtc-production $HOME/Development/balsamiq/convox-ops/bin/convox-wrapper'
alias b-convox-staging='envchain balsamiq-convox-staging $HOME/Development/balsamiq/convox-ops/bin/convox-wrapper'
# alias b-convox-ondeck='envchain balsamiq-convox-eu-6 $HOME/Development/balsamiq/convox-ops/bin/convox-wrapper'

# TODO: Instead create a new "fake" command in convox-wrapper (e.g., `convox instances docker ps`)
alias b-convox-production-docker-ps="b-convox-production foreach instances 'docker ps --no-trunc --format \"{{.Names}}\" | sort'"
# alias b-convox-rtc-production-docker-ps="b-convox-rtc-production foreach instances 'docker ps --no-trunc --format \"{{.Names}}\" | sort'"
alias b-convox-staging-docker-ps="b-convox-staging foreach instances 'docker ps --no-trunc --format \"{{.Names}}\" | sort'"
# alias b-convox-ondeck-docker-ps="b-convox-ondeck foreach instances 'docker ps --no-trunc --format \"{{.Names}}\" | sort'"

alias b-db-acetaia-production='( cd acetaia/infrastructure/ && nvm use && npm install && envchain balsamiq-aws-srlinternal bin/cli proxy production mysql )'
# TODO: convert to BIK:
# alias b-db-bottega-production='b-convox-production proxy 3329:convox-prod-bottega-mysql.cc5xfgbtx6kw.us-east-1.rds.amazonaws.com:3306'
alias b-db-swag-production='b-convox-production proxy 3339:convox-prod-swag-mysql.cc5xfgbtx6kw.us-east-1.rds.amazonaws.com:3306'
alias b-db-olio-staging='( cd olio/ && ./ssh-tunnel-staging.sh -i ~/.ssh/keys/balsamiq-olio-staging.pem )'
alias b-db-olio-feature='( cd olio/ && ./ssh-tunnel-feature.sh -i ~/.ssh/keys/balsamiq-olio-feature.pem )'
alias b-db-olio-production='( cd olio/ && ./ssh-tunnel-production.sh -i ~/.ssh/keys/balsamiq-olio-production.pem )'

# alias b-aws-llc='open -a "Balsamiq AWS LLC"'
# alias b-aws-srl-internal='open -a "Balsamiq AWS SRL internal"'

npm() {(
  export BALSAMIQ_NPM_AUTH_TOKEN="$(envchain balsamiq-private-npm-registry env | grep '^BALSAMIQ_NPM_AUTH_TOKEN' | cut -d '=' -f2-)"
  # PRIVATE_NPM_AUTH_TOKEN is the name of the original environment variable
  # picked by Stefano (?), but since I didn't like it I am promoting
  # `BALSAMIQ_NPM_AUTH_TOKEN`. However, since the original name is still in use
  # in various codebases, this double export is necessary.
  export PRIVATE_NPM_AUTH_TOKEN="$BALSAMIQ_NPM_AUTH_TOKEN"
  # Should we use `command npm "$@"` instead? See also `npx` below.
  command npm $*
)}
export -f npm

npx() {(
  export BALSAMIQ_NPM_AUTH_TOKEN="$(envchain balsamiq-private-npm-registry env | grep '^BALSAMIQ_NPM_AUTH_TOKEN' | cut -d '=' -f2-)"
  # PRIVATE_NPM_AUTH_TOKEN is the name of the original environment variable
  # picked by Stefano (?), but since I didn't like it I am promoting
  # `BALSAMIQ_NPM_AUTH_TOKEN`. However, since the original name is still in use
  # in various codebases, this double export is necessary.
  export PRIVATE_NPM_AUTH_TOKEN="$BALSAMIQ_NPM_AUTH_TOKEN"
  # `command npx $*` breaks `npx concurrently "echo foo" "echo bar"`
  command npx "$@"
)}
export -f npx

# b-npm() {
#   envchain balsamiq-private-npm-registry /bin/bash -ic 'export PRIVATE_NPM_AUTH_TOKEN=$BALSAMIQ_NPM_AUTH_TOKEN; npm'" $*"
# }
# b-node18-npm() {
#   envchain balsamiq-private-npm-registry /bin/bash -ic 'export PRIVATE_NPM_AUTH_TOKEN=$BALSAMIQ_NPM_AUTH_TOKEN; node18-npm'" $*"
# }
# b-node16-npm() {
#   envchain balsamiq-private-npm-registry /bin/bash -ic 'export PRIVATE_NPM_AUTH_TOKEN=$BALSAMIQ_NPM_AUTH_TOKEN; node16-npm'" $*"
# }
# b-node14-npm() {
#   envchain balsamiq-private-npm-registry /bin/bash -ic 'export PRIVATE_NPM_AUTH_TOKEN=$BALSAMIQ_NPM_AUTH_TOKEN; node14-npm'" $*"
# }
# b-node12-npm() {
#   envchain balsamiq-private-npm-registry /bin/bash -ic 'export PRIVATE_NPM_AUTH_TOKEN=$BALSAMIQ_NPM_AUTH_TOKEN; node12-npm'" $*"
# }
# alias b-npm-node18=b-node18-npm
# alias b-npm-node16=b-node16-npm
# alias b-npm-node14=b-node14-npm
# alias b-npm-node12=b-node12-npm

# b-npx() {
#   envchain balsamiq-private-npm-registry /bin/bash -ic 'export PRIVATE_NPM_AUTH_TOKEN=$BALSAMIQ_NPM_AUTH_TOKEN; npx'" $*"
# }
# b-node18-npx() {
#   envchain balsamiq-private-npm-registry /bin/bash -ic 'export PRIVATE_NPM_AUTH_TOKEN=$BALSAMIQ_NPM_AUTH_TOKEN; node18-npx'" $*"
# }
# b-node16-npx() {
#   envchain balsamiq-private-npm-registry /bin/bash -ic 'export PRIVATE_NPM_AUTH_TOKEN=$BALSAMIQ_NPM_AUTH_TOKEN; node16-npx'" $*"
# }
# b-node14-npx() {
#   envchain balsamiq-private-npm-registry /bin/bash -ic 'export PRIVATE_NPM_AUTH_TOKEN=$BALSAMIQ_NPM_AUTH_TOKEN; node14-npx'" $*"
# }
# b-node12-npx() {
#   envchain balsamiq-private-npm-registry /bin/bash -ic 'export PRIVATE_NPM_AUTH_TOKEN=$BALSAMIQ_NPM_AUTH_TOKEN; node12-npx'" $*"
# }
# alias b-npx-node18=b-node18-npx
# alias b-npx-node16=b-node16-npx
# alias b-npx-node14=b-node14-npx
# alias b-npx-node12=b-node12-npx

b-bootstrap--bw-atlassian() {
  source "$HOME/.sdkman/bin/sdkman-init.sh"
  sdk use java 8.0.332-tem
}

b-workon--bw-jira() {
  b-bootstrap--bw-atlassian
  node18-npm install --legacy-peer-deps

  #envchain balsamiq-private-npm-registry /bin/bash -c 'export PRIVATE_NPM_AUTH_TOKEN=$BALSAMIQ_NPM_AUTH_TOKEN; npx concurrently --names "postgres,redis,grunt,jira,logs,reload" --kill-others \
  #  "$(brew --prefix)/opt/postgresql@11/bin/postgres -D $(brew --prefix)/var/postgresql@11" \
  #  "$(brew --prefix)/opt/redis/bin/redis-server $(brew --prefix)/etc/redis.conf" \
  #  "npx onchange '"'"'src/main/js/**'"'"' --initial --kill -- \"$(brew --prefix)/opt/node@18/bin/node\" node_modules/.bin/grunt build" \
  #  "bash -c \"$(cat launchJira.sh) -DskipTests\"" \
  #  "npx wait-on http-get://localhost:2990/jira/ && tail -f target/jira/home/log/atlassian-jira.log" \
  #  "npx wait-on http-get://localhost:2990/jira/ && npx onchange '"'"'**'"'"' --exclude-path .gitignore --kill -- time atlas-package -DskipTests -Datlassian.webresource.disable.minification=true"' \
  #|| true
  npx concurrently --names "postgres,redis,grunt,jira,logs,reload" --kill-others \
    "$(brew --prefix)/opt/postgresql@11/bin/postgres -D $(brew --prefix)/var/postgresql@11" \
    "$(brew --prefix)/opt/redis/bin/redis-server $(brew --prefix)/etc/redis.conf" \
    "npx onchange '"'"'src/main/js/**'"'"' --initial --kill -- \"$(brew --prefix)/opt/node@18/bin/node\" node_modules/.bin/grunt build" \
    "bash -c \"$(cat launchJira.sh) -DskipTests\"" \
    "npx wait-on http-get://localhost:2990/jira/ && tail -f target/jira/home/log/atlassian-jira.log" \
    "npx wait-on http-get://localhost:2990/jira/ && npx onchange '"'"'**'"'"' --exclude-path .gitignore --kill -- time atlas-package -DskipTests -Datlassian.webresource.disable.minification=true" \
  || true
}

b-workon--bw-confluence() {
  b-bootstrap--bw-atlassian
  node18-npm install --legacy-peer-deps

  #envchain balsamiq-private-npm-registry /bin/bash -c 'export PRIVATE_NPM_AUTH_TOKEN=$BALSAMIQ_NPM_AUTH_TOKEN; npx concurrently --names "postgres,redis,grunt,confluence,reload" --kill-others \
  #  "$(brew --prefix)/opt/postgresql@11/bin/postgres -D $(brew --prefix)/var/postgresql@11" \
  #  "$(brew --prefix)/opt/redis/bin/redis-server $(brew --prefix)/etc/redis.conf" \
  #  "npx onchange '"'"'src/main/js/**'"'"' --initial --kill -- \"$(brew --prefix)/opt/node@18/bin/node\" node_modules/.bin/grunt build" \
  #  "bash -c \"$(cat launchConfluence.sh) -DskipTests\"" \
  #  "npx wait-on http-get://localhost:2990/confluence/ && npx onchange '"'"'**'"'"' --exclude-path .gitignore --kill -- time atlas-package -DskipTests -Datlassian.webresource.disable.minification=true"' \
  #|| true
  npx concurrently --names "postgres,redis,grunt,confluence,reload" --kill-others \
    "$(brew --prefix)/opt/postgresql@11/bin/postgres -D $(brew --prefix)/var/postgresql@11" \
    "$(brew --prefix)/opt/redis/bin/redis-server $(brew --prefix)/etc/redis.conf" \
    "npx onchange '"'"'src/main/js/**'"'"' --initial --kill -- \"$(brew --prefix)/opt/node@18/bin/node\" node_modules/.bin/grunt build" \
    "bash -c \"$(cat launchConfluence.sh) -DskipTests\"" \
    "npx wait-on http-get://localhost:2990/confluence/ && npx onchange '"'"'**'"'"' --exclude-path .gitignore --kill -- time atlas-package -DskipTests -Datlassian.webresource.disable.minification=true" \
  || true
}

b-workon--bas() {
  ( cd architecture/ && nvm use && npm install )
  ( cd src/ && nvm use && npm install --build-from-source --python=/usr/bin/python3 sqlite3 && npm install )

  # mysql@5.7-start

  // ask Stefano about NEW_LAMBDA_RTC_USE_JWT and either remove it or set it to true
  //NEW_LAMBDA_RTC_USE_JWT=false

  #'RTC_PUBLISH_KEY',

  #//'BAS_RTC_ENV_NAME',
  #//'RTC_SERVER_URL',
  #//'BAS_DEV_ENV_NAME',
  #//'S3_BUCKET_REGION',
  #//'S3_BUCKET_NAME',
  #//'KMS_REGION',
  #//'RTC_WEBHOOK_CALLBACK_BASE_URL',
  #
  #RTC_SERVER_URL
  #RTC_AUTH_TOKEN_SECRET
  #RTC_PUBLISH_KEY
  #NEW_LAMBDA_RTC_USE_JWT
  #RTC_SUBSCRIBE_KEY

  npx concurrently --names "redis,server" --kill-others \
    "$(brew --prefix)/opt/redis/bin/redis-server $(brew --prefix)/etc/redis.conf" \
    "( cd src/ && RTC_PUBLISH_KEY=pub-bas-ddb9d0ca-52ad-678f-b8ea-ddf525795f03 RTC_SERVER_URL=https://rtc-staging.balsamiq.com \"$(brew --prefix)/opt/node@18/bin/node\" server.js )" \
  || true
}

b-workon--cloud() {(
    mysql@8.0-start
    redis-start

    nvm use
    npm run start:development -- \
        --rtc-path=~/Development/balsamiq/rtc/ \
        --bas-path=~/Development/balsamiq/bas/ \
        --cloudauth-path=~/Development/balsamiq/cloudauth/ \
        --skip-tutorial \
        --cloud-envchain-namespace=balsamiq-cloud-development \
        --bas-envchain-namespace=balsamiq-bas-development \
        --rtc-envchain-namespace=balsamiq-rtc-development \
        --cloudauth-npm-server-script="server-local:ali"
)}
