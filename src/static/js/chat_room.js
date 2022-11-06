url_segs = window.location.pathname.split("/");
var room_name = url_segs[1]
var current_user = url_segs[2]

if (window.location.protocol == "https:") {
    var ws_scheme = "wss://";
} else {
    var ws_scheme = "ws://"
}
;

var ws = new WebSocket(ws_scheme + location.host + "/ws/" + room_name);
var messages = document.getElementById('messages')

function checkWebSocket(event) {
    if (ws.readyState === WebSocket.CLOSED) {
        console.log("WebSocket CLOSED: Reopening")
        ws = new WebSocket(ws_scheme + location.host + "/ws/" + room_name);
    }
}

ws.onmessage = function (event) {
    // Get message back from websocket and display
    var message = document.createElement('li');
    message.setAttribute('class', 'message');
    message.style.clear = 'both';

    var event_data = JSON.parse(event.data);
    var text_str = event_data.message
    var text = document.createTextNode(text_str)
    var sender_str = event_data.sender
    var sender = document.createTextNode(sender_str);

    console.log('Text Recieved: ' + text_str)

    var content_tag = document.createElement('div');
    content_tag.appendChild(text)
    content_tag.setAttribute("class", "content_tag")

    var sender_tag = document.createElement('div')
    sender_tag.appendChild(sender)
    sender_tag.setAttribute("class", "sender_tag")

    if (sender_str == current_user) {
        sender_tag.setAttribute("class", "sender_tag_right")
        content_tag.style.backgroundColor = '#ACEDFF'
        message.style.float = 'right'
        content_tag.style.float = 'right'
    } else {
        sender_tag.setAttribute("class", "sender_tag_left")
        content_tag.style.backgroundColor = '#CAE5FF'
        message.style.float = 'left'
        content_tag.style.float = 'left'
    }

    message.appendChild(content_tag)
    message.appendChild(sender_tag)

    messages.appendChild(message)
    messages.scrollTop = 999999999;
};

function sendMessage(event) {
    var input = document.getElementById("messageText")
    if (input.value.length > 0) {
        var message_obj = {
            'message': input.value, 'sender': current_user
        }
        ws.send(JSON.stringify(message_obj))
        input.value = ''
    }
    event.preventDefault()
}