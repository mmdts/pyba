import { Game, Locatable } from "./game.js";
import { Interactor } from "./interactor.js";
import * as C from "./constants.js";

/** @type {enum} */
const TICK_SUCCESS = 0;
/** @type {enum} */
const GAME_NOT_STARTED = 1;

export class Interface {
    /**
     * An interface defines how this client interacts with the server.
     * It is also responsible for managing inferior modules that make the client work.
     * The interface spawns its own instance of an Interactor, and takes
     * as parameters an instance of each of a WS and a Canvas.
     *
     * @typedef  {object} Options - The arguments required to start an interface.
     * @property {array}  room
     * @property {string} role
     *
     * @typedef  {object} GameState - The object received from the server.
     * @property {Game} game
     * @property {object} error - An optional error.
     *
     * @param {Options} options
     * @param {WS}      ws
     * @param {Canvas}  canvas
     */
    constructor ({room, role}, ws, canvas)  {
        if (!room?.length) {
            throw "Room needs to be set on options before interface is initialized.";
        }
        if (!C.ROLES.includes(role) && role !== "_") {
            throw `The role ${role} set on options is invalid.`;
        }
        this.room = room;
        this.role = role;

        this.player = new Locatable();
        this.game = new Game();
        this.droppedItemsPerGameTile = {};
        this.penancePerGameTile = {};
        this.text = [];

        this.interactor = null;

        this.ws = ws;
        this.canvas = canvas;
        this.ws.addReceiveListener(this.logListener.bind(this));
        this.ws.addReceiveListener(this.receiveListener.bind(this));
        this.ws.addReceiveListener(this.errorListener.bind(this));
    };

    /**
     * A listener that prints the game state, used for debugging.
     *
     * @param {GameState} json
     */
    logListener (json) {
        console.log("RECEIVED:", json);
    };

    /**
     * The basic listener which populates this.game, this.player, and this.text
     * from the server data.
     *
     * @param {GameState} json
     */
    receiveListener ({game}) {
        if (game === undefined) return;
        this.game = new Game(game);
        this.populateEntriesPerGameTile();
        this.player = this.game.players[this.role];
        this.text = this.game.text ?? [];
    };

    /**
     * A basic error listener which console.logs json.error if exists.
     *
     * @param {GameState} json
     */
    errorListener ({error}) {
        if (error === undefined) return;
        console.error("A server-side error was encountered.");
    };

    /**
     * The following six functions all send special types of actions that relate
     * to the formation of rooms / waves, rather than in-game player actions.
     *
     * This one creates a room.
     *
     * @param {enum} mode
     * @returns {Interface}
     */
    roomCreate (mode = C.ROOM_DELAY) {
        return this.sendAction("room_create", [this.role, mode]);
    };

    /**
     * Connects to an already existing room.
     *
     * @returns {Interface}
     */
    roomConnect () {
        return this.sendAction("room_connect", [this.role]);
    };

    /**
     * Starts a new wave. Can only be called by the principal player (who created the room).
     *
     * @param {number} wave_number
     * @param {string} runner_movements
     * @returns {Interface}
     */
    startWave (wave_number, runner_movements = "") {
        return this.sendAction("new_wave", [wave_number, runner_movements]);
    };

    /**
     * Toggles the game time passage mode.
     *
     * @param {enum} mode
     * @returns {Interface}
     */
    toggleMode (mode) {
        return this.sendAction("toggle_mode", [mode ? C.ROOM_PAUSE : C.ROOM_DELAY]);
    };

    /**
     * Steps when the mode is set to pause.
     *
     * @returns {Interface}
     */
    serverStep () {
        return this.sendAction("step", []);
    };

    /**
     * Polls the server using WS.sendEmpty, so that the socket connection does not drop.
     *
     * @returns {Interface}
     */
    poll () {
        this.ws.sendEmpty();
        return this;
    };

    /**
     * Checks if two locations are equal.
     *
     * @param {number[]} l1
     * @param {number[]} l2
     * @returns {boolean}
     */
    checkLocation (l1, l2) {
        return l1[0] === l2[0] && l1[1] === l2[1];
    }

    /**
     * This obnoxious monstrosity takes no arguments and returns nothing.
     * It just populates a variable called this.droppedItemsPerGameTile.
     * It also populates this.penancePerGameTile.
     *
     * The variables are a triple-nested object structure, where the the levels are:
     * Level | Keys                   | Note
     *     1 | "food", "eggs", "hnls" | droppedItemsPerGameTile: The three different types of dropped items.
     *     1 | "a", "d", "h", "s"     | penancePerGameTile: The four different species of penance.
     *     2 | y-coordinates          | Level 2 and 3 are basically a lookup on the
     *     3 | x-coordinates          | tile within that specific item category.
     */
    populateEntriesPerGameTile () {
        this.droppedItemsPerGameTile = { "eggs": {}, "food": {}, "hnls": {} };
        this.penancePerGameTile = { "a": {}, "d": {}, "h": {}, "s": {} };
        for (let i = 0; i < C.MAP_HEIGHT; i++) { // i is y, j is x.
            this.droppedItemsPerGameTile["food"][i] = {};
            this.droppedItemsPerGameTile["eggs"][i] = {};
            this.droppedItemsPerGameTile["hnls"][i] = {};
            this.penancePerGameTile["a"][i] = {};
            this.penancePerGameTile["d"][i] = {};
            this.penancePerGameTile["h"][i] = {};
            this.penancePerGameTile["s"][i] = {};
            for (let j = 0; j < C.MAP_WIDTH; j++) {
                this.droppedItemsPerGameTile["food"][i][j] = [];
                this.droppedItemsPerGameTile["eggs"][i][j] = [];
                this.droppedItemsPerGameTile["hnls"][i][j] = [];
                this.penancePerGameTile["a"][i][j] = [];
                this.penancePerGameTile["d"][i][j] = [];
                this.penancePerGameTile["h"][i][j] = [];
                this.penancePerGameTile["s"][i][j] = [];
                for (let key in this.game.wave.penance) {
                    if (this.game.wave.penance.hasOwnProperty(key)) {
                        for (let k = 0; k < this.game.wave.penance[key].length; k++) {
                            if (!this.checkLocation(this.game.wave.penance[key][k].location, [j, i])) continue;
                            this.penancePerGameTile[key][i][j].push(this.game.wave.penance[key][k]);
                        }
                    }
                }
                for (let k = 0; k < this.game.wave.dropped_food.length; k++) {
                    if (!this.checkLocation(this.game.wave.dropped_food[k].location, [j, i])) continue;
                    this.droppedItemsPerGameTile["food"][i][j].push(this.game.wave.dropped_food[k]);
                }
                for (let k = 0; k < this.game.wave.dropped_eggs.length; k++) {
                    if (!this.checkLocation(this.game.wave.dropped_eggs[k].location, [j, i])) continue;
                    this.droppedItemsPerGameTile["eggs"][i][j].push(this.game.wave.dropped_eggs[k]);
                }
                for (let k = 0; k < this.game.wave.dropped_hnls.length; k++) {
                    if (!this.checkLocation(this.game.wave.dropped_hnls[k].location, [j, i])) continue;
                    this.droppedItemsPerGameTile["hnls"][i][j].push(this.game.wave.dropped_hnls[k]);
                }
            }
        }
    }

    /**
     * Processes a game tick by doing the following 3 actions:
     * 1. Draw the original map (and create an interactor if not exists).
     * 2. Draw the map elements.
     * 3. Draw the inventory for non-spectators.
     * 4. Write the info.
     *
     * @returns {enum} - Returns an enum representing whether or not the tick succeeded.
     */
    tick () {
        if (!this.room?.length) {
            throw "Room needs to be set on options before interface starts ticking.";
        }
        // This check is important because the default values that values inside
        // game are initialized to will make sure that the rest of this function fails
        // if this.game is not initialized properly by the receiveListener.
        if (this.game.tick === null) {
            return GAME_NOT_STARTED;
        }

        if (!this.canvas.drawn) {
            // This part of the code should happen only once.
            this.canvas.drawMap(this.game.original_map);
            if (!this.interactor) {
                this.interactor = new Interactor(this);
            }
        }

        this.canvas.drawMapElements(this.game.self_map, this.droppedItemsPerGameTile, this.role);
        if (this.role !== "_")
            this.canvas.drawInventory(this.player.access_letter, this.player.inventory, this.interactor.highlightedItem);

        this.canvas.writeInfo(this.text);

        return TICK_SUCCESS;
    };

    /**
     * Sends an action using WS.send
     *
     * @param {string} action
     * @param {array} args
     * @returns {Interface}
     */
    sendAction (action, args) {
        if (!Array.isArray(args)) {
            throw "Args needs to be an array.";
        }
        if (action !== action + "") {
            throw "Action needs to be a string.";
        }

        if (this.role === "_" && action !== "room_connect") return this;

        this.ws.send({
            "room": this.room,
            "action": action,
            "args": args,
        });
        return this;
    };
}
