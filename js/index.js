$(function() {
    var ws = new WebSocket(window.location.href.replace("http", "ws") +'ws/echo');
    
    ws.onopen = function() {
        ws.onmessage = function(msg) {
            alert(msg.data);
        };
        
        alert("socket is open");
    }
    $("#test_button").click(function() {
        ws.send($("#text").val());
    });
});
