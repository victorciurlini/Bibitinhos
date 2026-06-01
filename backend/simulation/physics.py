import pymunk

# Define Collision Categories
COLLISION_CATEGORY_CREATURE = 1
COLLISION_CATEGORY_FOOD = 2
COLLISION_CATEGORY_WALL = 4

def create_space():
    space = pymunk.Space()
    space.gravity = (0.0, 0.0)
    space.damping = 0.9
    
    # Define 2000x2000 map boundaries
    map_width = 2000
    map_height = 2000
    
    static_body = space.static_body
    
    # Create the four walls
    walls = [
        pymunk.Segment(static_body, (0, 0), (map_width, 0), 0.0), # Bottom
        pymunk.Segment(static_body, (map_width, 0), (map_width, map_height), 0.0), # Right
        pymunk.Segment(static_body, (map_width, map_height), (0, map_height), 0.0), # Top
        pymunk.Segment(static_body, (0, map_height), (0, 0), 0.0) # Left
    ]
    
    for wall in walls:
        wall.elasticity = 1.0
        wall.friction = 0.5
        wall.filter = pymunk.ShapeFilter(categories=COLLISION_CATEGORY_WALL)
        space.add(wall)
        
    return space, map_width, map_height

class PhysicsEngine:
    def __init__(self):
        self.space, self.map_width, self.map_height = create_space()

    def step(self, dt):
        self.space.step(dt)
