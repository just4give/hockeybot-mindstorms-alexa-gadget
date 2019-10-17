/*
 HOCKEY BOT ALEXA SKILL CODE
*/



const Alexa = require('ask-sdk-core');
const Util = require('./util');
const Common = require('./common');

// The audio tag to include background music
const BG_MUSIC = '<audio src="soundbank://soundlibrary/ui/gameshow/amzn_ui_sfx_gameshow_waiting_loop_30s_01"/>';

// The namespace of the custom directive to be sent by this skill
const NAMESPACE = 'Custom.Hockeybot.Gadget';

// The name of the custom directive to be sent this skill
const NAME_CONTROL = 'control';

const SKILL_STATES = {
    START: '_START',
    GAME_IN_PROGRESS: '_GAME_IN_PROGRESS',
    HELP_STATE: '_HELP'
  };

const LaunchRequestHandler = {
    canHandle(handlerInput) {
        return Alexa.getRequestType(handlerInput.requestEnvelope) === 'LaunchRequest';
    },
    handle: async function(handlerInput) {

        let {
            attributesManager,
            requestEnvelope,
            responseBuilder
          } = handlerInput;

        //let request = handlerInput.requestEnvelope;
        let { apiEndpoint, apiAccessToken } = requestEnvelope.context.System;
        let apiResponse = await Util.getConnectedEndpoints(apiEndpoint, apiAccessToken);
        if ((apiResponse.endpoints || []).length === 0) {
            return handlerInput.responseBuilder
            .speak(`I couldn't find an EV3 Brick connected to this Echo device. Please check to make sure your EV3 Brick is connected, and try again.`)
            .getResponse();
        }

        // Store the gadget endpointId to be used in this skill session
        let endpointId = apiResponse.endpoints[0].endpointId || [];
        Util.putSessionAttribute(handlerInput, 'endpointId', endpointId);
        Util.putSessionAttribute(handlerInput, 'STATE', SKILL_STATES.START);

        // Set skill duration to 5 minutes (ten 30-seconds interval)
        Util.putSessionAttribute(handlerInput, 'duration', 10);
        
        // Set the token to track the event handler
        const token = handlerInput.requestEnvelope.request.requestId;
        Util.putSessionAttribute(handlerInput, 'token', token);

        return handlerInput.responseBuilder
            .speak("Welcome to Hockey Championship. To start a new game, just say BEGIN ...")
            .reprompt("To start a new game, just say BEGIN ...")
            .withShouldEndSession(false)
            .addDirective(Util.buildStartEventHandler(token,60000, {}))
            .getResponse();
    }
};

// Add the speed value to the session attribute.
// This allows other intent handler to use the specified speed value
// without asking the user for input.
const SetSpeedIntentHandler = {
    canHandle(handlerInput) {
        let {
            attributesManager,
            requestEnvelope
          } = handlerInput;

        return Alexa.getRequestType(handlerInput.requestEnvelope) === 'IntentRequest'
            && Alexa.getIntentName(handlerInput.requestEnvelope) === 'SetSpeedIntent';
    },
    handle: function (handlerInput) {

        // Bound speed to (1-100)
        let speed = Alexa.getSlotValue(handlerInput.requestEnvelope, 'Speed');
        speed = Math.max(1, Math.min(100, parseInt(speed)));
        Util.putSessionAttribute(handlerInput, 'speed', speed);

        return handlerInput.responseBuilder
            .speak(`speed set to ${speed} percent.`)
            .reprompt("awaiting command")
            .getResponse();
    }
};

// Construct and send a custom directive to the connected gadget with
// data from the MoveIntent request.
const MoveIntentHandler = {
    canHandle(handlerInput) {
        let {
            attributesManager,
            requestEnvelope
          } = handlerInput;

        return Alexa.getRequestType(handlerInput.requestEnvelope) === 'IntentRequest'
            && Alexa.getIntentName(handlerInput.requestEnvelope) === 'MoveIntent'
            && attributesManager.getSessionAttributes().STATE === SKILL_STATES.GAME_IN_PROGRESS;
    },
    handle: function (handlerInput) {
        const request = handlerInput.requestEnvelope;
        const direction = Alexa.getSlotValue(request, 'Direction');

        // Duration is optional, use default if not available
        const duration = Alexa.getSlotValue(request, 'Duration') || "5";

        // Get data from session attribute
        const attributesManager = handlerInput.attributesManager;
        const speed = attributesManager.getSessionAttributes().speed || "20";
        const endpointId = attributesManager.getSessionAttributes().endpointId || [];

        // Construct the directive with the payload containing the move parameters
        const directive = Util.build(endpointId, NAMESPACE, NAME_CONTROL,
            {
                type: 'move',
                direction: direction,
                duration: duration,
                speed: speed
            });

        const speechOutput = (direction === "brake")
            ?  "Applying brake"
            : `${direction} ${duration} seconds at ${speed} percent speed`;

        return handlerInput.responseBuilder
            .speak("OK")
            .reprompt("which direction?")
            .addDirective(directive)
            .getResponse();
    }
};

// Construct and send a custom directive to the connected gadget with data from
// the SetCommandIntent request.
const HitIntentHandler = {
    canHandle(handlerInput) {
        let {
            attributesManager,
            requestEnvelope
          } = handlerInput;

        return Alexa.getRequestType(handlerInput.requestEnvelope) === 'IntentRequest'
            && Alexa.getIntentName(handlerInput.requestEnvelope) === 'HitIntent';
    },
    handle: function (handlerInput) {

        let command = Alexa.getSlotValue(handlerInput.requestEnvelope, 'Command');
        const direction = Alexa.getSlotValue(handlerInput.requestEnvelope, 'Direction');

        if (!command) {
            return handlerInput.responseBuilder
                .speak("Can you repeat that?")
                .reprompt("What was that again?").getResponse();
        }

        const attributesManager = handlerInput.attributesManager;
        let endpointId = attributesManager.getSessionAttributes().endpointId || [];
        let speed = attributesManager.getSessionAttributes().speed || "40";

        // Construct the directive with the payload containing the move parameters
        let directive = Util.build(endpointId, NAMESPACE, NAME_CONTROL,
            {
                type: 'command',
                command: command,
                direction: direction||'left',
                speed: speed
            });

        return handlerInput.responseBuilder
            .speak('OK')
            .reprompt("awaiting command")
            .withShouldEndSession(false)
            .addDirective(directive)
            .getResponse();
    }
};

const GameStartHandler = {
    canHandle(handlerInput) {

        let {
            attributesManager,
            requestEnvelope
          } = handlerInput;

        return Alexa.getRequestType(handlerInput.requestEnvelope) === 'IntentRequest'
            && Alexa.getIntentName(handlerInput.requestEnvelope) === 'StartIntent'
            && attributesManager.getSessionAttributes().STATE === SKILL_STATES.START;
    },
    handle(handlerInput) {

        let {
            attributesManager,
            requestEnvelope,
            responseBuilder
          } = handlerInput;

        Util.putSessionAttribute(handlerInput, 'STATE', SKILL_STATES.GAME_IN_PROGRESS);
        const speakOutput = "<prosody> BRAVO! Let's begin...</prosody> ";
        const speed = attributesManager.getSessionAttributes().speed || "20";
        const endpointId = attributesManager.getSessionAttributes().endpointId || [];

        const directive = Util.build(endpointId, NAMESPACE, NAME_CONTROL,
        {
            type: 'start',
            direction: "forward",
            duration: "5",
            speed: speed
        });

        return handlerInput.responseBuilder
            .speak(speakOutput)
            .reprompt(speakOutput)
            .addDirective(directive)
            .getResponse();
    }
};

const ExpiredRequestHandler = {
    canHandle(handlerInput) {
        let {
            attributesManager,
            requestEnvelope
          } = handlerInput;

        return Alexa.getRequestType(handlerInput.requestEnvelope) === 'CustomInterfaceController.Expired'
    },
    handle(handlerInput) {
        console.log("== Custom Event Expiration Input ==");

        // Set the token to track the event handler
        const token = handlerInput.requestEnvelope.request.requestId;
        Util.putSessionAttribute(handlerInput, 'token', token);

        const attributesManager = handlerInput.attributesManager;
        let duration = attributesManager.getSessionAttributes().duration || 0;
        //duration = duration/2

        if (duration > 0) {
            Util.putSessionAttribute(handlerInput, 'duration', --duration);

            // Extends skill session
            const speechOutput = `${duration/2} minutes remaining. Awaiting commands.`;
            return handlerInput.responseBuilder
                .addDirective(Util.buildStartEventHandler(token, 60000, {}))
                .withShouldEndSession(false)
                .speak(speechOutput)
                .getResponse();
        }
        else {
            // End skill session
            return handlerInput.responseBuilder
                .speak("Skill duration expired. Goodbye.")
                .withShouldEndSession(true)
                .getResponse();
        }
    }
};

const EventsReceivedRequestHandler = {
    // Checks for a valid token and endpoint.
    canHandle(handlerInput) {
        let { request } = handlerInput.requestEnvelope;
        console.log('Request type: ' + Alexa.getRequestType(handlerInput.requestEnvelope));
        if (request.type !== 'CustomInterfaceController.EventsReceived') return false;

        const attributesManager = handlerInput.attributesManager;
        let sessionAttributes = attributesManager.getSessionAttributes();
        let customEvent = request.events[0];

        // Validate event token
        if (sessionAttributes.token !== request.token) {
            console.log("Event token doesn't match. Ignoring this event");
            return false;
        }

        // Validate endpoint
        let requestEndpoint = customEvent.endpoint.endpointId;
        if (requestEndpoint !== sessionAttributes.endpointId) {
            console.log("Event endpoint id doesn't match. Ignoring this event");
            return false;
        }
        return true;
    },
    handle(handlerInput) {

        console.log("== Received Custom Event ==");
        let customEvent = handlerInput.requestEnvelope.request.events[0];
        let payload = customEvent.payload;
        let name = customEvent.header.name;

        let speechOutput ="Event not recognized.";
        if (name === 'GAME_OVER') {
            let score = parseInt(payload.score);
            speechOutput = "Game over. You scored "+score+" goals!!!";
            return handlerInput.responseBuilder
                .speak(speechOutput, "REPLACE_ALL")
                .withShouldEndSession(true)
                .getResponse();
            
        } 
        return handlerInput.responseBuilder
            .speak(speechOutput, "REPLACE_ALL")
            .getResponse();
    }
};

// The SkillBuilder acts as the entry point for your skill, routing all request and response
// payloads to the handlers above. Make sure any new handlers or interceptors you've
// defined are included below. The order matters - they're processed top to bottom.
exports.handler = Alexa.SkillBuilders.custom()
    .addRequestHandlers(
        LaunchRequestHandler,
        GameStartHandler,
        SetSpeedIntentHandler,
        HitIntentHandler,
        MoveIntentHandler,
        ExpiredRequestHandler,
        EventsReceivedRequestHandler,
        Common.HelpIntentHandler,
        Common.CancelAndStopIntentHandler,
        Common.SessionEndedRequestHandler,
        Common.IntentReflectorHandler, // make sure IntentReflectorHandler is last so it doesn't override your custom intent handlers
    )
    .addRequestInterceptors(Common.RequestInterceptor)
    .addErrorHandlers(
        Common.ErrorHandler,
    )
    .lambda();