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
    - [ ] Item group system
        - [ ] Eg medkits all share a group and instead of having multiple of medkits, the one you would get is removed from world and a counter on your first is incremented by 1 or destroyed
        - [ ] Store and convo events can just increment counters instead of giving you one, but have one they can give you if you don't have one
        - [ ] Destroyed or removed from world event, triggered when item is moved to a special container out of play, and use it to send merchants copy of item back to them
- [ ] ASCII mapping to show layout
- [ ] Moving keeps track of xyz
    - [ ] Pathfinding, walk xyz tried to move you by checking.if you can move towards it
- [ ] Combat system
- [X] Conversation system
    - [X] Dialog prompts
    - [ ] Option to show a variable value at the end of the texts
    - [ ] Option for a text input instead of choices prompt
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
    - [ ] Set Goal state
    - [ ] Change value of other entity
    - [ ] Change exit values of a zone/change lock state/change exits
    - [ ] Set global flag
    - [X] Move an entity (including give/take items from inventories)
    - [ ] Set companion state (make entity follow player)
    - [X] Enter Conversation
    - [X] Exit Conversation
    - [ ] Begin Battle
    - [ ] Exit Battle
- [ ] Input redirect (to allow prompts to temporarily take user input instead of passing it to the command parser)
- [X] Personal configs, to allow the user to define settings across any story
    - [X] Write a default file if one doesn't exist
    - [X] aliases to shorten any other command string
- [ ] Goals System
- [X] User notes system
- [ ] special cli flags to bypass story load and go to built in app shells (dice roller, cards)
- [ ] Write configs and saves in to a global config directory, home?
    - [ ] Define the script location as home
    - [ ] Add that directory to PATH to allow easy access to `xyzzy` command
    - [ ] Move saves in to a sub /save directory
- [X] Save system
    - [X] using without a name quicksave files under a `quicksave` name
- [X] Utility Commands
    - [X] Dice roll
    - [X] Coin flip
    - [X] Choose from list
- [ ] JSON state pre-processor commands
    - [ ] Check for them after the state has been loaded and before the game loop
    - [ ] `extends: "other_entity_id"` / copies non-defined keys from another entity
- [ ] Other client interfaces
- [ ] Built-in deck of cards simulation
