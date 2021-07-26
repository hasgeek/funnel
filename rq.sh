#!/bin/sh

# For macOS: https://stackoverflow.com/a/52230415/78903
export OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES

flask rq worker funnel
