# What I built, and why

I built EdgeSentinel to practice the kind of work that sits between devices,
networks, and software. The goal was to have something I could run, break on
purpose, and explain in an Industrial IoT interview.

I kept it small: three pretend machines, one Python app, one local database, and
four problems. The machines are fake. The TCP messages, input checks, saved events,
alerts, and browser interface really work.

## The problem I wanted to explore

A warning by itself is not very helpful. "Something is wrong" leaves the next
person guessing. I wanted the app to answer three questions:

1. What did we actually observe?
2. Which messages support that answer?
3. What should someone check next?

That is why every alert has message IDs and every helper response has source labels.
You can open the original data and check the explanation yourself.

## Follow one hot-machine incident

Suppose you click **Make the press run hot**.

The simulator starts reporting 95 C for `press-01`. It sends that value as a JSON
message over TCP to a listener on the same computer. The gateway checks that the
message has the required fields and sensible types, then saves it in SQLite.

The temperature rule compares 95 with the fixed demo limit of 80. Since 95 is
above 80, it creates an alert that points to that saved message. Repeated high
readings update the same active alert instead of making a new warning every second.

When you click **Explain this alert**, the helper reads the alert and its messages,
checks the device's recent activity, and searches the local guides. It returns a
short explanation and investigation steps, each with a source. It does not decide
that a motor is broken, and it does not try to cool anything down.

Click **Start / return to normal** and the next normal sensor reading clears the
active temperature warning. The old alert stays in history so you can inspect it.

## Why I chose these tools

| Choice | Why it fits this project | The tradeoff |
| --- | --- | --- |
| Python and asyncio | TCP clients, timers, and the web server fit in one small process | Blocking work can delay everything else |
| FastAPI | Clear routes, input validation, and generated API docs | It is still a web app that needs careful lifecycle handling |
| SQLite | A real database in one local file, with no server setup | This design is not meant for a large fleet |
| Plain HTML/CSS/JS | Anyone can run it without a frontend build | UI state is managed by a small hand-written script |
| Explicit rules | Easy to explain, test, and reproduce | No learned baseline or adaptation to real equipment |
| Local guides and a fixed helper | Works without keys and cannot invent a model-generated diagnosis | It cannot reason freely or answer arbitrary questions |

## The engineering details I cared about

- Bad JSON should not stop the listener. Each line is checked on its own.
- Messages should have a size limit. The gateway accepts at most 4096 bytes per line.
- An alert should point to real saved evidence, not a made-up example.
- Missing-device detection needs its own timer. A silent device cannot send the
  message that tells us it has gone silent.
- Time rules should use arrival time. A sender can put any timestamp in a message.
- The helper should only read. Demo controls and investigation tools are separate paths.
- Reset should stop built-in traffic and close in-flight clients before clearing rows.
- The app should say what it cannot prove. A missing check-in does not prove a
  hardware fault, and a claimed sender address does not prove identity.

## What I would say in an interview

"I built a local simulator that turns device messages into traceable alerts. I
used simple rules because I wanted predictable behavior and tests before adding
models. The interesting part is the evidence path: each alert links to saved
messages, and the helper combines those messages with local guides. I can explain
where each answer came from. It is not a production industrial security tool."

The [interview guide](interview-guide.md) has the module walkthrough and questions.
The [verification notes](verification.md) say exactly what was run and what was not.
