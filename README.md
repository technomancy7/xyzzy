# (> xyzzy

![Example](https://raw.githubusercontent.com/technomancy7/xyzzy/master/example.png)

## (> what is it
Xyzzy is a small script that let's you easily create text adventure games just by creating a "world" in a pure json format.
The end-goal is that the basic library is extensive enough that almost any story can be created without needing to write any code, with a format that is simple  yet flexible enough that other interfaces, interpreters, GUI's, etc, can be built to use the same data.
Basically attempting to bring the old idea of z-machine formats in to a modern framework.

Xyzzy is written in the [Arturo](https://arturo-lang.io/) language.


## (> how's it goin'
(To expand as time goes)
- [ ] Inventory
    - [X] Pickup items
    - [X] Drop items
    - [ ] Use items
    - [ ] Equipment system
- [ ] Combat system
- [ ] Conversation system
    - [ ] Dialog prompts
- [ ] Music system?
    - [ ] Maybe using ffmpeg
- [ ] Movement
    - [ ] Events for entering zones
    - [ ] Events for first-time entering zones
    - [ ] System for entities to follow the player
    - [ ] Update auto-complete automatically each movement to include new entity list
- [ ] Event keywords
    - [X] Generic text
    - [X] Message as character
    - [ ] Change value of other entity
    - [ ] Change exit values of a zone/change lock state
    - [ ] Set global flag
    - [ ] Move an entity (including give/take items from inventories)
    - [ ] Set companion state (make entity follow player)
    - [ ] Enter Conversation
    - [ ] Exit Conversation
    - [ ] Begin Battle
    - [ ] Exit Battle
- [ ] Input redirect (to allow prompts to temporarily take user input instead of passing it to the command parser)
- [ ] Personal configs, to allow the user to define settings across any story
    - [ ] aliases to shorten any other command string
- [ ] Save system
    - [ ] save/load.local <name> - to store the save data within the story file
    - [ ] save/load.file <name> - to store the save as a separate file
    - [ ] using without a name quicksave files under a `quicksave` name
