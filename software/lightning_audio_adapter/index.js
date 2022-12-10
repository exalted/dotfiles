const { execSync } = require("child_process");

const ADAPTER_NAME = "Lightning Audio Adapter";

// `SwitchAudioSource` is available via `brew install switchaudio-osx`
const audioDeviceFound = execSync("SwitchAudioSource -a", {
  encoding: "utf-8",
})
  .split("\n")
  .find((x) => x.includes(ADAPTER_NAME));

if (audioDeviceFound) {
  console.log(`${ADAPTER_NAME} is detected. Nothing to do.`);
  return;
}

const adapterFound = execSync("system_profiler SPAudioDataType", {
  encoding: "utf-8",
})
  .split("\n")
  .find((x) => x.includes(ADAPTER_NAME));

if (!adapterFound) {
  console.log(`${ADAPTER_NAME} is not attached. Nothing to do.`);
  return;
}

let output;

// `uhubctl` is available via `brew tap mvp/uhubctl https://github.com/mvp/uhubctl && brew install uhubctl`
output = execSync(`uhubctl --search '${ADAPTER_NAME}' --exact`, {
  encoding: "utf-8",
});

const noCompatibleDevicesDetectedMessage = "No compatible devices detected!";
if (output.split("\n")[0] === noCompatibleDevicesDetectedMessage) {
  // Since at this point `system_profiler` has already found it, this should
  // never happen, but if it did, then we wouldn't know what to do next, hence
  // the error:
  throw new Error(noCompatibleDevicesDetectedMessage);
}

let location;

try {
  ({
    groups: { location },
  } = output.split("\n")[0].match(/hub (?<location>[\d.-]+)/i));
} catch (error) {
  throw new Error("Couldn't detected the location", { cause: error });
}

let port;

try {
  ({
    groups: { port },
  } = output.split("\n")[1].match(/port (?<port>\d+)/i));
} catch (error) {
  throw new Error("Couldn't detected the port", { cause: error });
}

console.log(
  `Found ${ADAPTER_NAME} at location '${location}' on port '${port}'`
);
console.groupCollapsed();
console.debug(`|\n| DEBUG:\n|`);
console.debug(
  output
    .split("\n")
    .map((line) => `| ${line}`)
    .join("\n")
);
console.groupEnd();
output = undefined;

process.stdout.write(
  `Cycling ${ADAPTER_NAME} at location '${location}' on port '${port}' ...`
);

output = execSync(
  `uhubctl --action cycle --location ${location} --ports ${port} --exact`,
  {
    encoding: "utf-8",
  }
);

console.log(" ✅");
console.groupCollapsed();
console.debug(`|\n| DEBUG:\n|`);
console.debug(
  output
    .split("\n")
    .map((line) => `| ${line}`)
    .join("\n")
);
console.groupEnd();
output = undefined;

// // This random sleep of 10 seconds seems to be enough to cycle the USB port
// // power before attempting again. However, in case this isn't good enough, in
// // future you could redo `SwitchAudioSource -a` check (see at the very top) with
// // a timeout until the adapter is detected.
// execSync("sleep 10");
