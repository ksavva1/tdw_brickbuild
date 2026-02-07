from tdw.controller import Controller
from tdw.tdw_utils import TDWUtils
from tdw.add_ons.third_person_camera import ThirdPersonCamera
from magnebot import Magnebot, Arm, ActionStatus


class MagnebotLogCabin(Controller):

    TABLE_SURFACE_Y = 0.42
    SPAWN_Y         = 0.46
    BOX_SCALE       = 0.5
    BOX_FULL_H      = 0.12
    CRUISE_ALT      = 1.20
    GRASP_DY        = 0.02
    DROP_CLEARANCE  = 0.15

    STACK_X = 0.0
    STACK_Z = 0.0

    # ── per-block placement: (offset_x, offset_z, layer, yaw) ────────
    PLACEMENTS = [
        # (offset_x, offset_z, layer, yaw)
        ( 0.00,  0.00, 0,   0),   # Block 0: layer 1 centre
        ( 0.00, -0.07, 1,  90),   # Block 1: layer 2 -z side
        ( 0.00,  0.07, 1,  90),   # Block 2: layer 2 +z side
        ( 0.00,  0.00, 2, 180),   # Block 3: layer 3 centre
    ]

    # ── block spawn positions on the table ────────────────────────────
    BLOCK_STARTS = [
        {"x": -0.20, "z":  0.20},   # Block 0 – Red
        {"x": -0.20, "z": -0.20},   # Block 1 – Blue
        {"x":  0.20, "z":  0.20},   # Block 2 – Green
        {"x":  0.05, "z": -0.20},   # Block 3 – Yellow  (closer for reach)
    ]

    BLOCK_COLORS = [
        {"r": 0.90, "g": 0.10, "b": 0.10, "a": 1.0},
        {"r": 0.15, "g": 0.15, "b": 0.90, "a": 1.0},
        {"r": 0.10, "g": 0.75, "b": 0.15, "a": 1.0},
        {"r": 0.95, "g": 0.80, "b": 0.10, "a": 1.0},
    ]

    BLOCK_NAMES = ["Red", "Blue", "Green", "Yellow"]

    # ──────────────────────────────────────────────────────────────────

    def __init__(self):
        super().__init__(launch_build=True)

    def _settle(self, n: int = 25):
        for _ in range(n):
            self.communicate([])

    def _do(self, bot: Magnebot, label: str):
        print(f"  ▸ {label} …")
        while bot.action.status == ActionStatus.ongoing:
            self.communicate([])
        self.communicate([])
        status = bot.action.status
        tag = "✔" if status == ActionStatus.success else "✘"
        print(f"    {tag} {status}")

    # ── main ──────────────────────────────────────────────────────────

    def run(self):
        camera = ThirdPersonCamera(
            position={"x": 1.1, "y": 1.6, "z": -1.3},
            look_at={"x": 0, "y": 0.55, "z": 0},
            avatar_id="obs",
        )
        bot = Magnebot(
            position={"x": -0.85, "y": 0, "z": 0},
            rotation={"x": 0, "y": 90, "z": 0},
        )
        self.add_ons.extend([camera, bot])

        # ---------- scene + objects -----------------------------------
        table_id  = self.get_unique_id()
        block_ids = [self.get_unique_id() for _ in range(4)]

        cmds = [TDWUtils.create_empty_room(12, 12)]

        cmds.extend(self.get_add_physics_object(
            model_name="small_table_green_marble",
            object_id=table_id,
            position={"x": 0, "y": 0, "z": 0},
            scale_factor={"x": 0.8, "y": 0.5, "z": 0.8},
        ))

        for i in range(4):
            bx = self.BLOCK_STARTS[i]["x"]
            bz = self.BLOCK_STARTS[i]["z"]
            cmds.extend(self.get_add_physics_object(
                model_name="iron_box",
                object_id=block_ids[i],
                position={"x": bx, "y": self.SPAWN_Y, "z": bz},
                scale_factor={"x": self.BOX_SCALE,
                              "y": self.BOX_SCALE,
                              "z": self.BOX_SCALE},
            ))
            cmds.append({"$type": "set_mass", "id": block_ids[i], "mass": 0.8})
            cmds.append({"$type": "set_color",
                         "color": self.BLOCK_COLORS[i],
                         "id": block_ids[i]})

        self.communicate(cmds)
        self._settle(50)

        # ── stacking loop ─────────────────────────────────────────────
        for i, bid in enumerate(block_ids):

            off_x, off_z, layer, yaw = self.PLACEMENTS[i]
            bx = self.BLOCK_STARTS[i]["x"]
            bz = self.BLOCK_STARTS[i]["z"]

            place_x = self.STACK_X + off_x
            place_z = self.STACK_Z + off_z
            place_y = self.TABLE_SURFACE_Y + layer * self.BOX_FULL_H
            drop_y  = place_y + self.DROP_CLEARANCE

            print(f"\n{'='*55}")
            print(f"  BLOCK {i} ({self.BLOCK_NAMES[i]})  │  "
                  f"layer {layer+1}  │  yaw {yaw}°")
            print(f"  Place at ({place_x:.2f}, {place_y:.2f}, {place_z:.2f})")
            print(f"{'='*55}")

            # ── GRASP ────────────────────────────────────────────────

            # Torso for grasp: capped at 0.9 (proven reachable)
            grasp_torso = min(0.6 + layer * 0.15, 0.9)
            bot.slide_torso(height=grasp_torso)
            self._do(bot, f"Torso to {grasp_torso:.2f} for grasp")

            # Reach for block on table
            grasp_y = self.TABLE_SURFACE_Y + self.GRASP_DY
            bot.reach_for(
                target={"x": bx, "y": grasp_y, "z": bz},
                arm=Arm.right,
            )
            self._do(bot, "Reach for block")

            # Grasp
            bot.grasp(target=bid, arm=Arm.right)
            self._do(bot, "Grasp")
            self._settle(10)

            # Lift straight up
            bot.reach_for(
                target={"x": bx, "y": self.CRUISE_ALT, "z": bz},
                arm=Arm.right,
            )
            self._do(bot, "Lift up")

            # ── PLACE ────────────────────────────────────────────────

            # Raise torso for placement if needed (layer 2+)
            full_torso = 0.6 + layer * 0.15
            if full_torso > grasp_torso:
                bot.slide_torso(height=min(full_torso, 1.5))
                self._do(bot, f"Raise torso to {full_torso:.2f} for placement")

            # Move above placement position
            bot.reach_for(
                target={"x": place_x,
                        "y": self.CRUISE_ALT,
                        "z": place_z},
                arm=Arm.right,
            )
            self._do(bot, "Move above placement")

            # Lower to drop height
            bot.reach_for(
                target={"x": place_x,
                        "y": drop_y,
                        "z": place_z},
                arm=Arm.right,
            )
            self._do(bot, "Lower to drop height")
            self._settle(15)

            # Release
            print("  ▸ Releasing …")
            self.communicate({"$type": "detach_from_magnet",
                              "id": bot.robot_id,
                              "arm": "right",
                              "object_id": bid})
            self._settle(50)

            # ── SNAP & FREEZE ────────────────────────────────────────

            self.communicate([
                {"$type": "teleport_object",
                 "id": bid,
                 "position": {"x": place_x,
                              "y": place_y,
                              "z": place_z}},
                {"$type": "rotate_object_to",
                 "rotation": {"x": 0, "y": 0, "z": 0, "w": 1},
                 "id": bid},
            ])

            if yaw != 0:
                self.communicate([
                    {"$type": "rotate_object_by",
                     "angle": float(yaw),
                     "axis": "yaw",
                     "id": bid,
                     "is_world": True},
                ])

            self.communicate([
                {"$type": "set_kinematic_state",
                 "id": bid,
                 "is_kinematic": True,
                 "use_gravity": False},
            ])
            self._settle(10)
            print(f"    ✔ Block {i} locked at y={place_y:.3f}, yaw={yaw}°")

            # ── RETRACT (exact v2 sequence that works for 3 blocks) ──

            bot.reach_for(
                target={"x": self.STACK_X,
                        "y": self.CRUISE_ALT,
                        "z": self.STACK_Z},
                arm=Arm.right,
            )
            self._do(bot, "Retract up")

            bot.reach_for(
                target={"x": -0.50, "y": self.CRUISE_ALT, "z": 0},
                arm=Arm.right,
            )
            self._do(bot, "Retract lateral")

            bot.reset_arm(arm=Arm.right)
            self._do(bot, "Reset arm")
            self._settle(20)

        # ── finish ───────────────────────────────────────────────────
        print(f"\n{'='*55}")
        print("Complete")
        print(f"{'='*55}\n")

        while True:
            self.communicate([])


if __name__ == "__main__":
    c = MagnebotLogCabin()
    c.run()