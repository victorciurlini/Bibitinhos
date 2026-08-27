import pymunk

# Define Collision Categories
COLLISION_CATEGORY_CREATURE = 1
COLLISION_CATEGORY_FOOD = 2
COLLISION_CATEGORY_WALL = 4

def create_space():
    space = pymunk.Space()
    space.gravity = (0.0, 0.0)
    space.damping = 0.35  # arrasto tipo agua: retem ~35% da velocidade por segundo sem propulsao
                          # (era 0.9 = ~90%/s, quase sem arrasto perceptivel - sensacao "flutuante")
    
    # Define map boundaries
    map_width = 1400   # BIT-22: era 2000 — 2000x2000 e esparso demais para reproducao sexuada emergir
    map_height = 1400  # (metade da area ~ dobro da densidade; frontend auto-escala por data.width/height)
    
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
