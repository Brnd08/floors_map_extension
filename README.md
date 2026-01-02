# Floor Maps Entension
Floor Maps Extension is an inkscape extension that allows you to add navigations specification required to use the [Flutter Map Widget](https://github.com/ADC-Studio/floors_map_widget). 

# Link pattern
Each point / building objects have a unique id and a list of neighbours. The Linking patter is described by the following regex expressions:


    POINT_ID_REGEX = re.compile(r'^point-(\d+)(?:=([\d-]*))?$')
    # point-43=44-39-45
    # │     │  └‒‒└‒‒└‒‒‒‒‒ unique IDs of connected neighbors
    # │     └‒‒‒‒‒ unique ID of the object
    # └‒‒‒‒‒ class of the object - point
    
    BUILDING_ID_REGEX = re.compile(r'^((?!point-)[a-zA-Z]+)-(?:([a-zA-Z]+)-)?(\d+)=([\d]+)$')
    # stairs-elevator-1=2
    # │      │        │ └‒‒‒‒‒ unique ID of the connected entrance point (there can be only one)
    # │      │        └‒‒‒‒‒ unique ID of the object
    # │      └‒‒‒‒‒ subtype of the object (required for stairs and toilet)
    # └‒‒‒‒‒ class of the object
# Funtionalities
As of today the extension allows you sped up your floor map creation by providing a set of diferent operations from connecting points, addition of buildings up to deletion of no-longer-linked points. 

Main page: 
<img width="879" height="533" alt="image" src="https://github.com/user-attachments/assets/6ea61958-856d-4539-8089-f83897872d1e" />

## Point Connection
Given a series of selected svg elements will obtain only the ellipses & circle shapes to link them by updating their id ittribute. 

Each one will be assigned a unique point id and will have a list of linked neighbour ids. 

The extension allows you to specify wether to draw a visual line representing each connection (you can specify the color and stroke of such lines). 

<img width="879" height="533" alt="image" src="https://github.com/user-attachments/assets/34c527a2-d634-4cad-b234-0d8a9cb93cdf" />


NOTE: It is pending to implement smart connect features to reduce overhead when creating bigger floor maps. 

Example results: 
<img width="1452" height="526" alt="image" src="https://github.com/user-attachments/assets/d2d2c67f-539e-49d5-a17c-c96b9f0d4d0a" /> <img width="1452" height="526" alt="image" src="https://github.com/user-attachments/assets/fee795cb-e434-4671-99de-6b0415b977d0" />



## Building Connection
Given a serias of selected svg elements will asign a unique building id, draw an entrance point (a common point used to note the entrance of a building) and link the created point id on the building svg element id attribute

Allows you to set the size, color fill and stroke of the entrance points as well as its positioning relative to the building's building box. 

<img width="879" height="533" alt="image" src="https://github.com/user-attachments/assets/c645f6f8-f1c3-40d5-a09f-b6843e239bb1" />

Example results: 

<img width="1452" height="526" alt="image" src="https://github.com/user-attachments/assets/1f61cf91-e84a-41ed-aca2-e24e4db4f8f6" /><img width="1452" height="526" alt="image" src="https://github.com/user-attachments/assets/61c5ef6f-93cf-4640-9577-a522a5efaf68" />



