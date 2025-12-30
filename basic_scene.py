from tdw.controller import Controller
from tdw.tdw_utils import TDWUtils
from tdw.add_ons.third_person_camera import ThirdPersonCamera

class SimpleTableScene(Controller):
    def __init__(self):
        # Launch TDW window
        super().__init__(launch_build=True)

    def run(self):
        # Setup camera
        camera = ThirdPersonCamera(position={"x": 2, "y": 1.6, "z": -1},
                                   look_at={"x": 0, "y": 0, "z": 0},
                                   avatar_id="a")
        self.add_ons.append(camera)

        # Prepare object IDs
        table_id = self.get_unique_id()
        box_id = self.get_unique_id()
        
        commands = []
        
        # Create empty room
        commands.append(TDWUtils.create_empty_room(12, 12))
        
        # Add table
        commands.extend(self.get_add_physics_object(model_name="small_table_green_marble",
                                                    object_id=table_id,
                                                    position={"x": 0, "y": 0, "z": 0}))

        # Add box at y=1.0 so it is above the table
        commands.extend(self.get_add_physics_object(model_name="iron_box",
                                                    object_id=box_id,
                                                    position={"x": 0, "y": 1.0, "z": 0}))

        self.communicate(commands)
        print("Scene loaded with table and iron box.")

        # Keep window open
        while True:
            self.communicate([])

if __name__ == "__main__":
    c = SimpleTableScene()
    c.run()