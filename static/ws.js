import io from "./io.js";

const SENT_EVENT_NAME = "client_action";
const RECEIVED_EVENT_NAME = "game_state";
const WEBSOCKET_ONLY = true;

export class WS {
    /**
     * A websocket wrapper, allows for sending client actions, sending empty polls,
     * and adding receive listeners to handle the received data.
     */
    constructor () {
        this.fns = [];
        this.ws = WEBSOCKET_ONLY ? io({transports: ['websocket'], upgrade: false}) : io();
        this.ws.on(RECEIVED_EVENT_NAME, (message) => {
            // The event.data object we receive has the game and the player.
            // If no game has been started yet, game is null. If no player has been set yet, player is null.
            for (let i = 0; i < this.fns.length; i++) {
                this.fns[i](JSON.parse(message));
            }
        });
    };

    /**
     * Sends the object as a stringified JSON, with the event name: SENT_EVENT_NAME.
     *
     * @typedef  {object} PlayerEvent
     * @property {array}  args
     * @property {string} action
     * @property {string} room
     *
     * @param {PlayerEvent} json
     * @returns {WS} - For chaining
     */
    send (json) {
        this.ws.emit(SENT_EVENT_NAME, JSON.stringify(json));
        return this;
    };

    /**
     * Sends an empty websocket event with the event name: SENT_EVENT_NAME.
     *
     * @returns {WS} - For chaining
     */
    sendEmpty () {
        this.ws.emit(SENT_EVENT_NAME);
        return this;
    };

    /**
     * Adds an event listener to the list of listeners this WS fires upon receiving server data.
     *
     * @param {function(object)} fn - Takes a JSON parsed object that came from the server.
     * @returns {WS} - For chaining.
     */
    addReceiveListener (fn) {
        this.fns.push(fn);
        return this;
    };
}
