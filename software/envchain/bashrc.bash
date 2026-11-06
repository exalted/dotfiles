envchain() {
    # USAGE: `envchain --list NAMESPACE` to get the list of variables defined
    #        with their values
    #
    # This relies on undocumented `envchain --list NAMESPACE` behavior to get
    # the list of variables and changes the behavior of that specific execution
    # to print the variables with their values.

    if [ "$#" -ne 2 ] || [ "$1" != "--list" ]; then
        command envchain "$@"
        return
    fi

    local namespace
    namespace="$2"

    local env_vars
    env_vars=$(command envchain "--list" "$namespace")

    command envchain "$namespace" sh -c "printenv | grep --extended-regexp '^(${env_vars//$'\n'/|})='"
}
