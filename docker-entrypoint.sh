#!/bin/bash
set -e

# Inject AWS SSM parameters into ENV
if [[ -n AWS_SSM_PREFIX ]]; then
    pattern="AWS SSM: %s -> %s\n"

    for group in $(echo "$AWS_SSM_PREFIX" | tr "," "\n")
    do
        while IFS= read -r param
        do
            name=$(echo "$param" | cut -f1)
            value=$(echo "$param" | cut -f2)

            if [[ -z value ]]; then
                continue
            fi

            if [[ -z ${!name} ]]; then
                export "$name"="$value"

                if [[ -n AWS_SSM_DEBUG ]]; then
                    printf "$pattern" "$name" "$value"
                else
                    printf "$pattern" "$name" "Done"
                fi
            else
                printf "$pattern" "$name" "Skip"
            fi
        done <<< "$(aws ssm get-parameters-by-path --path $group --with-decryption --output text | cut -f4,6 | sed $'s:^[^\t]*/::g')"
    done
fi

# Execute command
exec "$@"
