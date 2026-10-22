#!/bin/sh
# Run ONLY after obtaining supported, authorized shell access to your own G1.
# Reads version, ports and file metadata. Does not print passwords, keys or hashes.
# No sudo, services, CAN socket, reboot, writes, migrations or updates.
if command -v node >/dev/null 2>&1; then
    NODE_BIN=$(command -v node)
elif command -v nodejs >/dev/null 2>&1; then
    NODE_BIN=$(command -v nodejs)
else
    printf '%s\n' 'Node interpreter unavailable; no changes made.'
    exit 1
fi
"$NODE_BIN" <<'NODE'
var fs = require('fs');
var result = {nodeVersion: process.version, platform: process.platform,
    credentialsPrinted: false, deviceWrites: 0, canOpened: false};
function read(path) {
    try {
        if (fs.statSync(path).size > 4194304) return null;
        return fs.readFileSync(path, 'utf8');
    } catch (error) { return null; }
}
function fileMetadata(path) {
    try {
        var stat = fs.statSync(path);
        return {exists: true, bytes: stat.size, mode: (stat.mode & 511).toString(8)};
    } catch (error) { return {existsOrReadable: false}; }
}
var base = '/var/local/rocon-g1';
var version = read(base + '/version');
result.applicationVersion = version && /^\s*\d+\s*$/.test(version) ? parseInt(version, 10) : null;
result.localConfig = fileMetadata(base + '/config/parameters.js');
var config = read(base + '/config/parameters.js');
var port = config && config.match(/web_port\s*:\s*(\d+)/);
result.literalWebPortOverride = port ? parseInt(port[1], 10) : null;
// No require/eval of the installed parameters.js or other application code.
result.defaultDataDirectory = {};
['user', 'apikey'].forEach(function(name) {
    var path = '/home/root/.rocon/' + name + '.json';
    var metadata = fileMetadata(path);
    var text = read(path);
    if (text !== null) {
        try {
            var data = JSON.parse(text);
            metadata.entryCount = Array.isArray(data) ? data.length : null;
        } catch (error) { metadata.validJson = false; }
    }
    result.defaultDataDirectory[name] = metadata;
});
result.listeningTcpPorts = [];
['/proc/net/tcp', '/proc/net/tcp6'].forEach(function(path) {
    var text = read(path);
    if (text === null) return;
    text.split('\n').slice(1).forEach(function(line) {
        var columns = line.trim().split(/\s+/);
        if (columns.length > 3 && columns[3] === '0A') {
            var port = parseInt(columns[1].split(':')[1], 16);
            if (result.listeningTcpPorts.indexOf(port) < 0) result.listeningTcpPorts.push(port);
        }
    });
});
result.listeningTcpPorts.sort(function(a, b) {return a-b;});
result.notes = ['Default directory only; custom data path requires separate review.',
    'No credentials, EEPROM, private SSH key or configuration contents exported.'];
console.log(JSON.stringify(result, null, 2));
NODE
