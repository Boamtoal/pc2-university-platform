#!/bin/sh
set -eu
BASE=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
if [ -n "${LCPC_BUILD_JAVA_HOME:-}" ]; then
  LCPC_JAVAC="$LCPC_BUILD_JAVA_HOME/bin/javac"
  LCPC_JAR="$LCPC_BUILD_JAVA_HOME/bin/jar"
elif [ -n "${JAVA_HOME:-}" ]; then
  LCPC_JAVAC="$JAVA_HOME/bin/javac"
  LCPC_JAR="$JAVA_HOME/bin/jar"
elif [ -x /Library/Java/JavaVirtualMachines/temurin-17.jdk/Contents/Home/bin/javac ]; then
  LCPC_JAVAC=/Library/Java/JavaVirtualMachines/temurin-17.jdk/Contents/Home/bin/javac
  LCPC_JAR=/Library/Java/JavaVirtualMachines/temurin-17.jdk/Contents/Home/bin/jar
else
  LCPC_JAVAC=$(command -v javac)
  LCPC_JAR=$(command -v jar)
fi
mkdir -p "$BASE/lcpc/build"
"$LCPC_JAVAC" --release 17 -cp "$BASE/lib/*:$BASE/lcpc/build:$BASE/work/wti/WebTeamInterface-1.1/WebTeamInterface-1.1.jar" -d "$BASE/lcpc/build" "$BASE"/lcpc/src/*.java
printf 'Premain-Class: LocalOnlyAgent\n\n' > "$BASE/lcpc/build/MANIFEST.MF"
"$LCPC_JAR" cfm "$BASE/lcpc/build/local-only-agent.jar" "$BASE/lcpc/build/MANIFEST.MF" -C "$BASE/lcpc/build" LocalOnlyAgent.class -C "$BASE/lcpc/build" 'LocalOnlyAgent$1.class' -C "$BASE/lcpc/build" 'LocalOnlyAgent$1$1.class'
printf 'Premain-Class: JudgeGuardAgent\n\n' > "$BASE/lcpc/build/JUDGE-MANIFEST.MF"
"$LCPC_JAR" cfm "$BASE/lcpc/build/judge-guard-agent.jar" "$BASE/lcpc/build/JUDGE-MANIFEST.MF" -C "$BASE/lcpc/build" JudgeGuardAgent.class -C "$BASE/lcpc/build" 'JudgeGuardAgent$1.class' -C "$BASE/lcpc/build" JudgeGuardPolicy.class
