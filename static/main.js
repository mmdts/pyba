/* TODO: BUILD
 *       Add spawn box border (by checking on first tick before any penance spawn, should still be init. letter, add id)
 *       Add border to player target location box.
 *       Add SCRIPTING.
 *       Make other 3 players bots.
 *       Build bots.
 *       Add checkbox to make self bot (spectate mode).
 *       Add change wave / (re)start wave option.
 *       Add tick duration definition, and ticking.
 *       Add help button and overlay (click hammer for repair trap, etc).
 *       Add call right click menu at the other side.
 *       Build the info log at the bottom.
 *
 * TODO: BUILD
 *       Chomp messages.
 *       Poison hitsplats.
 *       Side HP bars.
 */
import $ from "./jquery.js";
import { v4 as uuidv4 } from "./uuid.min.js";
import { Canvas } from "./canvas.js";
import { Interface } from "./interface.js";
import { WS } from "./ws.js";
import * as C from "./constants.js";

const FPS = 20;
const CLICK_FPS = 9;

const $sideWaveNumber = $("#number");
const $sideWaveTick = $("#tick");
const $sideCallsSent = $("#sent");
const $sideCallsReceived = $("#received");
const $sideCallsRequired = $("#required");
const $sideTrap = $("#trap");

const $roomIdRo = $("#room_id_ro");
const $role = $("#role");
const $createButton = $("#create_button");
const $createForm = $("#create");

const $roomIdRw = $("#room_id_rw");
const $connectButton = $("#connect_button");
const $connectForm = $("#connect");

const $copyButton = $("#copy_button");

const $waveNumber = $("#wave_number");
const $runnerMovements = $("#runner_movements");
const $waveButton = $("#wave_button");
const $waveSelectForm = $("#wave_select");

const $waveStepCheckbox = $("#wave_step_checkbox");
const $waveStepButton = $("#wave_step_button");

function disableForms (roomId) {
    $roomIdRo.val(roomId);
    $copyButton.prop("disabled", false);
    $createButton.prop("disabled", true);
    $connectButton.prop("disabled", true);
    $createForm.off();
    $connectForm.off();
}

$(function () {
    $copyButton.prop("disabled", true);
})

$copyButton.on("click", function () {
    $roomIdRo.select();
    document.execCommand('copy',false);
    document.getSelection().removeAllRanges();
});

document.addEventListener("copy", function(e) {
  e.preventDefault();
  if (e.clipboardData) {
    e.clipboardData.setData("text/plain", window.iface.room);
  }
});

$createForm.on("submit", function (e) {
    e.preventDefault();
    e.stopPropagation();
    let room = uuidv4();

    window.iface = new Interface({
        "room": room,
        "role": $role.val(),
    }, new WS(), new Canvas());

    // Set the value of the read only field in case we need to copy it for an invite.
    disableForms(room);

    // Create a new room.
    let mode = C.ROOM_DELAY;
    if ($waveStepCheckbox.is(":checked")) {
        mode = C.ROOM_PAUSE;
    }
    window.iface.roomCreate(mode);

    // Run the frame tick function.
    window.processFrameInterval = window.setInterval(processFrame, 1000 / FPS);
    window.processClickFrameInterval = window.setInterval(processClickFrame, 1000 / CLICK_FPS);
    return false;
});

$connectForm.on("submit", function (e) {
    e.preventDefault();
    e.stopPropagation();

    window.iface = new Interface({
        "room": $roomIdRw.val(),
        "role": $role.val(),
    }, new WS(), new Canvas());

    disableForms($roomIdRw.val());

    // Connect to an existing room.
    window.iface.roomConnect();

    // Run the frame tick function.
    window.interval = window.setInterval(processFrame, 1000 / FPS);
    return false;
});

$waveSelectForm.on("submit", function (e) {
    e.preventDefault();
    e.stopPropagation();

    // Start a wave.
    window.iface.startWave(+$waveNumber.val(), $runnerMovements.val());

    return false;
});

$waveStepCheckbox.on('change', function (e) {
    e.preventDefault();
    e.stopPropagation();

    // Toggle mode between step and delay.
    window.iface.toggleMode($waveStepCheckbox.is(":checked"));

    return false;
});

$waveStepButton.on('click', function (e) {
    e.preventDefault();
    e.stopPropagation();

    // Toggle mode to step.
    if (!$waveStepCheckbox.is(":checked")) {
        $waveStepCheckbox.prop('checked', true);
    }

    // Step a single step.
    window.iface.serverStep();

    return false;
});

$role.on('change', function () {
    if ($role.val() === "_") {
        $waveStepButton.prop("disabled", true);
        $waveStepCheckbox.prop("disabled", true);
        $createButton.prop("disabled", true);
        $waveButton.prop("disabled", true);
    } else {
        $waveStepButton.prop("disabled", false);
        $waveStepCheckbox.prop("disabled", false);
        $createButton.prop("disabled", false);
        $waveButton.prop("disabled", false);
    }
});


function g(key) {
    let first_key = key === "received_call" || key === "correct_call" ?
        window.iface?.role :
        C.CALL_PAIR[window.iface?.role]
    ;

    return C.NAMES[first_key ?? "_"]?.[+window.iface?.player?.[key] ?? "_"] ?? "";
}

function initializeSide () {
        $sideWaveNumber.text(`Wave: ${+(window.iface?.game?.wave?.number ?? -1) + 1}`);
        $sideWaveTick.text(`Tick: ${window.iface?.game?.wave?.relative_tick ?? ""}`);
        $sideTrap.text(`Trap Charges: ${window.iface?.game?.wave?.game_objects?.trap?.charges ?? ""}`);
        $sideCallsReceived.text(`${g("received_call")} (Correct: ${g("correct_call")})`);
        $sideCallsRequired.text(g("required_call"));
        $sideCallsSent.text(g("sent_call"));
}

function processFrame () {
    try {
        window.iface.poll();
        window.iface.tick();
        initializeSide();
    } catch (e) {
        window.clearInterval(window.processFrameInterval);
        throw e;
    }
}

function processClickFrame () {
    try {
        window.iface.canvas.drawClick();
    } catch (e) {
        window.clearInterval(window.processClickFrameInterval);
        throw e;
    }
}

$(initializeSide);

// For debugging purposes.
window.$ = $;
