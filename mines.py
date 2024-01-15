import random
import sys
import pygame
from pygame.locals import *
import time

# Initialize pygame
pygame.init()

# Colors
BLACK = pygame.Color(0, 0, 0)
WHITE = pygame.Color(255, 255, 255)
GREY = pygame.Color(128, 128, 128)
LIGHT_GREY = pygame.Color(200, 200, 200)
RED = pygame.Color(255, 0, 0)
GREEN = pygame.Color(0, 255, 0)
BLUE = pygame.Color(0, 0, 255)
background_color = BLACK
mines_rem_bg_color = pygame.Color(200, 30, 30)
mines_rem_font_color = BLACK
unk_rem_bg_color = pygame.Color(200, 100, 30)
unk_rem_font_color = BLACK
timer_bg_color = pygame.Color(30, 200, 100)
timer_font_color = BLACK
border_color = BLUE
unknown_box_color = GREY
known_box_color = LIGHT_GREY
mine_box_color = RED

num_colors = {1: BLUE,
              2: pygame.Color(0, 200, 0),
              3: RED,
              4: pygame.Color(0, 0, 128),
              5: pygame.Color(128, 0, 0),
              6: pygame.Color(0, 128, 128),
              7: BLACK,
              8: GREY}

# Mouse controls
LEFT = 1
RIGHT = 3

# Frames-per-second limit
FPS = pygame.time.Clock()
FPS_LIMIT = 60

# Pixel size of individual boxes
box_size = 24

# Minimum window dimensions
min_win_width = 350
min_win_height = 200

# Font properties
font = pygame.font.SysFont('segoeui', 18, True)
sb_font = pygame.font.SysFont('segoeui', 18)

# Time (seconds) before next game
RESET_TIME = 0.5


# TODO  I need to remove the dependence on pixels and pixel coordinates to define and interact with a box - interaction
#       should only be through an indexing system of some sort


class BoxGraphics:
    def __init__(self, x: int, y: int, dim: int, display_surf: pygame.Surface, color: pygame.Color):
        self._x = x
        self._y = y
        self._dim = dim
        self.display_surf = display_surf
        self.color = color
        self.surf = pygame.Surface((self.dim, self.dim))
        self.surf.fill(self.color)
        self.rect = self.surf.get_rect(center=(int(self.x + self.dim / 2), int(self.y + self.dim / 2)))
        self.display_surf.blit(self.surf, self.rect)

    @property
    def x(self):
        return self._x

    @x.setter
    def x(self, value):
        self._x = value

    @property
    def y(self):
        return self._y

    @y.setter
    def y(self, value):
        self._y = value

    @property
    def dim(self):
        return self._dim

    @dim.setter
    def dim(self, value):
        self._dim = value

    def resize(self, new_dim):
        self.dim = new_dim

    def show_number(self, n_neighbors):
        num = font.render(str(n_neighbors), True, num_colors[n_neighbors])
        width = num.get_rect().width
        height = num.get_rect().height
        left = int((self.rect.width - width) / 2)
        top = int((self.rect.height - height) / 2)
        num.get_rect().update((left, top), (width, height))
        self.surf.blit(num, pygame.Rect(left, top, width, height))
        self.display_surf.blit(self.surf, self.rect)

    def update_color(self, color):
        self.color = color
        self.surf.fill(self.color)
        self.display_surf.blit(self.surf, self.rect)


class Box:
    def __init__(self, box_id, box_graphics_obj):
        self._id = box_id
        self.graphics_obj = box_graphics_obj
        self.is_mine = False
        self.is_revealed = False
        self.is_protected = False
        self.n_neighbors = 0

    def get_id(self):
        return self._id

    def reveal(self):
        if not self.is_revealed and not self.is_protected:
            self.is_revealed = True
            if self.is_mine:
                self._update_color(mine_box_color)
            else:
                self._update_color(known_box_color)
                if self.n_neighbors > 0:
                    self._show_number()
            pygame.display.update()
        return self.n_neighbors if not self.is_mine else -1

    def _update_color(self, color):
        self.graphics_obj.update_color(color)

    def toggle_protect(self):
        if not self.is_revealed:
            if not self.is_protected:
                self.is_protected = True
                self._update_color(BLUE)
            else:
                self.is_protected = False
                self._update_color(GREY)
            return self.is_mine, self.is_protected
        return False, None

    def set_mine(self):
        self.is_mine = True

    def _show_number(self):
        self.graphics_obj.show_number(self.n_neighbors)

    def get_neighbor_ids(self, neighbor_info):
        n_rows, n_cols, width_start, height_start, width_step, height_step = neighbor_info
        col = int((self.graphics_obj.x - width_start) / width_step)
        row = int((self.graphics_obj.y - height_start) / height_step)
        ids = []
        for r in range(row - 1, row + 2):
            if r < 0 or r >= n_rows:
                continue
            for c in range(col - 1, col + 2):
                if c < 0 or c >= n_cols or (r == row and c == col):
                    continue
                ids.append(c * n_rows + r)
        return ids


class Grid:
    def __init__(self, dims, num_mines, _box_size=39, offsets=(10, 50, 10), headless=False, solver=None):
        self.headless = headless
        self.solver = solver
        self.boxes = {}
        self.n_mines = num_mines
        self.n_mines_protected = 0
        self.n_unknown = dims[0] * dims[1]
        self.n_protected = 0
        self.exploded = False
        self.is_locked = False
        self.n_rows = dims[0]
        self.n_cols = dims[1]
        self._box_size = _box_size
        self._width_offset = offsets[0]
        self._height_top_offset = offsets[1]
        self._height_bot_offset = offsets[2]
        self._t0 = 0
        if not self.headless:
            window_pad_scale = 1.1
            self._win_width = round(self.n_cols * (box_size + 1) * window_pad_scale) + 2 * self._width_offset
            self._win_width += int(self._win_width % 2)
            self._win_width = max(self._win_width, min_win_width)
            self._win_height = (round(self.n_rows * (box_size + 1) * window_pad_scale) + self._height_top_offset
                                + self._height_bot_offset)
            self._win_height += int(self._win_height % 2)
            self._win_height = max(self._win_height, min_win_height)
            self.display_surf = pygame.display.set_mode((self._win_width, self._win_height))
            self.display_surf.fill(background_color)
            pygame.display.set_caption("Paul's Extreme Minesweeper")
        self._make_board()

    def _make_board(self):
        if not self.headless:
            # Draw bounding rectangle
            nw = (self._width_offset, self._height_top_offset)
            ne = (self._win_width - self._width_offset, self._height_top_offset)
            sw = (self._width_offset, self._win_height - self._height_bot_offset)
            se = (self._win_width - self._width_offset, self._win_height - self._height_bot_offset)
            pygame.draw.line(self.display_surf, border_color, nw, ne)  # TOP
            pygame.draw.line(self.display_surf, border_color, sw, se)  # BOTTOM
            pygame.draw.line(self.display_surf, border_color, nw, sw)  # LEFT
            pygame.draw.line(self.display_surf, border_color, ne, se)  # RIGHT

            # Define pixel dimensions of grid
            self.height_start = self._height_top_offset + int((self._win_height - self._height_top_offset
                                                               - self._height_bot_offset
                                                               - self.n_rows * (self._box_size + 1)) / 2)
            self.height_stop = (self._win_height - self.height_start + self._height_top_offset
                                - self._height_bot_offset - self.n_rows % 2)
            self.width_start = int((self._win_width - self.n_cols * (self._box_size + 1)) / 2)
            self.width_stop = self._win_width - self.width_start - self.n_cols % 2
            self.width_step = self.height_step = self._box_size + 1

        # TODO this is where the pixel dependency needs to be replaced
        # Create Boxes in a grid and assign each a unique ID
        box_id = 0
        for i in range(self.width_start, self.width_stop, self.width_step):
            for j in range(self.height_start, self.height_stop, self.height_step):
                if not self.headless:
                    graphics_obj = BoxGraphics(i, j, self._box_size, self.display_surf, color=unknown_box_color)
                else:
                    graphics_obj = None
                self.boxes[(int((i - self.width_start) / self.width_step),
                            int((j - self.height_start) / self.height_step))] = Box(box_id, graphics_obj)
                box_id += 1

        # Save info needed to calculate neighbors for convenience
        self.neighbor_info = (self.n_rows, self.n_cols, self.width_start, self.height_start,
                              self.width_step, self.height_step)

        # Draw scoreboard
        if not self.headless:
            self._make_scoreboard()

    def _start_timer(self):
        self._t0 = time.time()
        return self._update_timer()

    def _update_timer(self):
        timer_min = int((time.time() - self._t0) // 60)
        timer_sec = int((time.time() - self._t0) % 60)
        return timer_min, timer_sec

    def _make_scoreboard(self):
        # Scoreboard surface
        self.sb_left_surf = pygame.Surface((int((self._win_width - 2 * self._width_offset) / 3.),
                                            self._height_top_offset - 2 * self._width_offset))
        self.sb_middle_surf = pygame.Surface((int((self._win_width - 2 * self._width_offset) / 3.),
                                              self._height_top_offset - 2 * self._width_offset))
        self.sb_right_surf = pygame.Surface((int((self._win_width - 2 * self._width_offset) / 3.),
                                             self._height_top_offset - 2 * self._width_offset))
        self.sb_left_surf.fill(mines_rem_bg_color)
        self.sb_middle_surf.fill(unk_rem_bg_color)
        self.sb_right_surf.fill(timer_bg_color)
        # Mines remaining
        self.mines_rem_str = f'Mines: {self.n_mines - self.n_mines_protected} / {self.n_mines}'
        self.mines_rem_surf = sb_font.render(self.mines_rem_str, True, mines_rem_font_color, mines_rem_bg_color)
        width = self.mines_rem_surf.get_rect().width
        height = self.mines_rem_surf.get_rect().height
        left = int((self.sb_left_surf.get_rect().width - width) / 2)
        top = int((self.sb_left_surf.get_rect().height - height) / 2)
        self.mines_rem_dims = (left, top, width, height)
        self.mines_rem_surf.get_rect().update(self.mines_rem_dims)
        # Unknown boxes remaining
        self.unk_rem_str = f'Unk: {self.n_unknown} / {self.n_rows * self.n_cols}'
        self.unk_rem_surf = sb_font.render(self.unk_rem_str, True, unk_rem_font_color, unk_rem_bg_color)
        width = self.unk_rem_surf.get_rect().width
        height = self.unk_rem_surf.get_rect().height
        left = int((self.sb_middle_surf.get_rect().width - width) / 2)
        top = int((self.sb_middle_surf.get_rect().height - height) / 2)
        self.unk_rem_dims = (left, top, width, height)
        self.unk_rem_surf.get_rect().update(self.unk_rem_dims)
        # Timer
        timer_min, timer_sec = self._start_timer()
        self.timer_str = '{}:{}'.format(timer_min, str(timer_sec).zfill(2))
        self.timer_surf = sb_font.render(self.timer_str, True, timer_font_color, timer_bg_color)
        width = self.timer_surf.get_rect().width
        height = self.timer_surf.get_rect().height
        left = int((self.sb_right_surf.get_rect().width - width) / 2)
        top = int((self.sb_right_surf.get_rect().height - height) / 2)
        self.timer_dims = (left, top, width, height)
        self.timer_surf.get_rect().update(self.timer_dims)
        # Make text
        self._update_scoreboard()

    def _update_scoreboard(self):
        # First, remove current text
        # Mines remaining
        self.mines_rem_surf = sb_font.render(self.mines_rem_str, True, mines_rem_bg_color, mines_rem_bg_color)
        self.sb_left_surf.blit(self.mines_rem_surf, self.mines_rem_dims)
        self.display_surf.blit(self.sb_left_surf, (self._width_offset, self._width_offset))
        self.mines_rem_str = f'Mines: {self.n_mines - self.n_mines_protected} / {self.n_mines}'
        self.mines_rem_surf = sb_font.render(self.mines_rem_str, True, mines_rem_font_color, mines_rem_bg_color)

        # Unknown boxes remaining
        self.unk_rem_surf = sb_font.render(self.unk_rem_str, True, unk_rem_bg_color, unk_rem_bg_color)
        self.sb_middle_surf.blit(self.unk_rem_surf, self.unk_rem_dims)
        self.display_surf.blit(self.sb_middle_surf,
                               (self._width_offset + int((self._win_width - 2 * self._width_offset) / 3.),
                                self._width_offset))
        self.unk_rem_str = f'Unk: {self.n_unknown} / {self.n_rows * self.n_cols}'
        self.unk_rem_surf = sb_font.render(self.unk_rem_str, True, unk_rem_font_color, unk_rem_bg_color)

        # Timer
        self.timer_surf = sb_font.render(self.timer_str, True, timer_bg_color, timer_bg_color)
        self.sb_right_surf.blit(self.timer_surf, self.timer_dims)
        self.display_surf.blit(self.sb_right_surf,
                               (self._width_offset + int((self._win_width - 2 * self._width_offset) * 2 / 3.),
                                self._width_offset))
        timer_min, timer_sec = self._update_timer()
        self.timer_str = '{}:{}'.format(timer_min, str(timer_sec).zfill(2))
        self.timer_surf = sb_font.render(self.timer_str, True, timer_font_color, timer_bg_color)

        # Next, add the new text
        self.sb_left_surf.blit(self.mines_rem_surf, self.mines_rem_dims)
        self.sb_middle_surf.blit(self.unk_rem_surf, self.unk_rem_dims)
        self.sb_right_surf.blit(self.timer_surf, self.timer_dims)

        # Put scoreboard on display
        self.display_surf.blit(self.sb_left_surf,   (self._width_offset, self._width_offset))
        self.display_surf.blit(self.sb_middle_surf,
                               (self._width_offset + int((self._win_width - 2 * self._width_offset) / 3.),
                                self._width_offset))
        self.display_surf.blit(self.sb_right_surf,
                               (self._width_offset + int((self._win_width - 2 * self._width_offset) * 2 / 3.),
                                self._width_offset))

    def reset(self):
        self.__init__((self.n_rows, self.n_cols), self.n_mines, self._box_size,
                      (self._width_offset, self._height_top_offset, self._height_bot_offset),
                      self.headless, self.solver)

    def expand_neighbors(self, box):
        neighbor_ids = box.get_neighbor_ids(self.neighbor_info)
        [self.reveal(self._id_to_box(neighbor_id)) for neighbor_id in neighbor_ids
         if not self._id_to_box(neighbor_id).is_revealed]

    def _id_to_box(self, box_id):
        return [box for box in self.boxes.values() if box.get_id() == box_id][0]

    def reveal(self, box):
        if not box.is_protected:
            n_neighbor_mines = box.reveal()
            self.n_unknown -= 1
            self.exploded = n_neighbor_mines == -1
            if n_neighbor_mines == 0:
                self.expand_neighbors(box)

    def toggle_protect(self, box):
        # TODO number of mines does not decrease on scoreboard if an incorrect tile is protected
        is_mine, is_protected = box.toggle_protect()
        if is_protected is not None:
            if is_protected:
                self.n_mines_protected += int(is_mine)
                self.n_protected += 1
                self.n_unknown -= 1
            else:
                self.n_mines_protected -= int(is_mine)
                self.n_protected -= 1
                self.n_unknown += 1

    def _check_win(self):
        win_str, bg_color = None, None
        if (self.n_mines - self.n_mines_protected <= 0 and self.n_mines_protected == self.n_protected
                and self.n_unknown == 0):
            win_str = 'YOU WIN!'
            bg_color = GREEN
            bg_color.a = 100
            print('Win!')
        elif self.exploded:
            win_str = 'YOU LOSE!'
            bg_color = RED
            bg_color.a = 100
            print('Lose!')
        if win_str:
            if not self.headless:
                win_font = pygame.font.SysFont('segoeui', 48, bold=True)
                win_font_surf = win_font.render(win_str, True, pygame.Color(0, 0, 0, 255))
                win_font_size = win_font_surf.get_size()
                win_bg_surf = pygame.Surface(self.display_surf.get_size(), pygame.SRCALPHA)
                win_bg_surf.fill(bg_color)
                width = win_bg_surf.get_rect().width
                height = win_bg_surf.get_rect().height
                left = int((self._win_width - width) / 2)
                top = int((self._win_height - height) / 2)
                win_bg_surf.blit(win_font_surf, (int((win_bg_surf.get_width() - win_font_size[0]) / 2.),
                                                 int((win_bg_surf.get_height() - win_font_size[1]) / 2.)))
                self.display_surf.blit(win_bg_surf, (left, top))
                pygame.display.update()
            self.is_locked = True
            return True
        return False

    def _first_move(self):
        # TODO clean this up to align with the flow of the main loop
        # Get the first click, and make sure it isn't a mine
        if not self.headless:
            pygame.display.update()
            pygame.event.clear()
            while True:
                event = pygame.event.wait()
                if event.type == QUIT:
                    pygame.quit()
                    sys.exit()
                elif event.type == MOUSEBUTTONUP:
                    # Find box that was clicked
                    m_pos = pygame.mouse.get_pos()
                    target = [box for box in self.boxes.values() if box.graphics_obj.rect.collidepoint(*m_pos)]

                    if target and event.button == LEFT:
                        target = target[0]
                        clicked_box_id = target.get_id()
                        neighbor_ids = target.get_neighbor_ids(self.neighbor_info)

                        # Pick boxes randomly to have mines, making sure the current one has none
                        max_tries = int(1e4)
                        tries = 0
                        mine_ids = None
                        while tries < max_tries:
                            mine_ids = random.sample(range(self.n_rows * self.n_cols), self.n_mines)
                            if clicked_box_id not in mine_ids:
                                if not any(neighbor in mine_ids for neighbor in neighbor_ids):
                                    break
                            tries += 1
                        if tries >= max_tries:
                            raise RuntimeError('Too many iterations attempted. Could not find a valid starting point.')

                        # Set mines
                        for mine_id in mine_ids:
                            for box in self.boxes.values():
                                if box.get_id() == mine_id:
                                    box.is_mine = True

                        # Exit the loop
                        break
        else:
            while True:
                action, target = self.solver.get_action(self)
                clicked_box_id = target.get_id()
                neighbor_ids = target.get_neighbor_ids(self.neighbor_info)
                # Pick boxes randomly to have mines, making sure the current one has none
                max_tries = int(1e4)
                tries = 0
                mine_ids = None
                while tries < max_tries:
                    mine_ids = random.sample(range(self.n_rows * self.n_cols), self.n_mines)
                    if clicked_box_id not in mine_ids:
                        if not any(neighbor in mine_ids for neighbor in neighbor_ids):
                            break
                    tries += 1
                if tries >= max_tries:
                    raise RuntimeError('Too many iterations attempted. Could not find a valid starting point.')
                # Set mines
                for mine_id in mine_ids:
                    for box in self.boxes.values():
                        if box.get_id() == mine_id:
                            box.is_mine = True
                # Exit the loop
                break

        # Compute each box's number of neighboring mines
        for box_id, box in self.boxes.items():
            box.n_neighbors = sum(mine_id in mine_ids for mine_id in box.get_neighbor_ids(self.neighbor_info))

        # Reveal the first one
        self.reveal(target)

    # def _receive_next_user_move(self):
    #     for event in pygame.event.get():
    def _process_player_action(self, event) -> (int, Box):
        target = None
        action = None
        # Check if the player took an action
        if event.type == MOUSEBUTTONUP and not self.is_locked:
            # Find box that was selected (if any)
            m_pos = pygame.mouse.get_pos()
            target = [box for box in self.boxes.values() if box.graphics_obj.rect.collidepoint(*m_pos)]

            # If a box was clicked, take an action
            if target:
                target = target[0]
                assert isinstance(target, Box)
                # Left click will reveal the box
                if event.button == LEFT:
                    action = 0
                # Right click will toggle being protected
                elif event.button == RIGHT:
                    action = 1

        return action, target

    def _do_action(self, action: int, target: Box) -> None:
        if action == 0:
            self.reveal(target)
        elif action == 1:
            self.toggle_protect(target)

    def run(self, single_game: bool = False) -> None:
        self._first_move()
        self._t0 = time.time()
        if not self.headless:
            self._update_scoreboard()
        reset = False
        reset_t0 = None

        # Main game loop
        while True:
            if not self.headless:
                pygame.display.update()
            else:
                raise RuntimeError("Headless mode not implemented.")

            # Check if the game needs to be reset
            if reset and (time.time() - reset_t0) > RESET_TIME:
                if single_game:
                    return
                self.reset()
                pygame.event.clear()
                reset = False
                self._first_move()
                self._t0 = time.time()

            # Check for an input
            for event in pygame.event.get():
                if event.type == QUIT:
                    pygame.quit()
                    sys.exit()
                # -> Put this back in the for loop above ->
                if not reset:
                    # TODO need to pull headless mode out of event check, and make it so only clicks
                    #  are accepted (not mouse movement)
                    if not self.headless:
                        action, target = self._process_player_action(event)
                        # action, target = self.solver.get_action(self)
                    else:
                        # Receive a target and action.
                        action, target = self.solver.get_action(self)

                    if target:
                        # Perform the action
                        self._do_action(action, target)

                        # After the action is taken, update the scoreboard accordingly
                        if not self.headless:
                            self._update_scoreboard()

                        # Check if the game is over
                        reset = self._check_win()
                        reset_t0 = time.time()
                # -> Put this back in the for loop above ->

            if not self.headless:
                if not self.is_locked:
                    self._update_scoreboard()

                # Limit the frame rate - tick forward one step
                FPS.tick(FPS_LIMIT)


class Solver:
    def __init__(self, _solver_type='rl') -> None:
        self.type = _solver_type

    def get_action(self, grid: Grid) -> (int, Box):
        # Make random guesses
        action = random.randint(0, 1)
        target = None
        i = 0
        while i < 100:
            target = grid._id_to_box(random.randint(0, grid.n_rows * grid.n_cols - 1))
            if target.is_revealed:
                i += 1
            else:
                break

        # Use keyboard input
        # while True:
        #     str_in = input("Next Move (action, target_id): ")
        #     action, target = str_in.split(',')
        #     action = int(action)
        #     target = grid._id_to_box(int(target.strip()))
        #     if target.is_revealed:
        #         print("Target box is already revealed. Pick another box.")
        #     else:
        #         break
        return action, target


difficulties = {'easy':         {'dims': (8, 8),    '_box_size': box_size, 'num_mines': 10},
                'intermediate': {'dims': (16, 16),  '_box_size': box_size, 'num_mines': 40},
                'expert':       {'dims': (16, 30),  '_box_size': box_size, 'num_mines': 99},
                'extreme':      {'dims': (9, 9),    '_box_size': box_size, 'num_mines': 35},
                'extremer':     {'dims': (16, 30),  '_box_size': box_size, 'num_mines': 170},
                'debug':        {'dims': (5, 4),    '_box_size': box_size, 'num_mines': 2}}


if __name__ == "__main__":
    # Run game
    _difficulty = 'debug'
    _headless = False
    _solver = Solver()
    grid = Grid(headless=_headless, solver=_solver, **difficulties[_difficulty])
    grid.run()


# SHORT TERM
# TODO make "headless" mode

# MEDIUM TERM
# TODO think about dynamically solving the board as the player progresses to avoid guessing

# LONG TERM
# TODO think about solvers - algorithmic, supervised learning, reinforcement learning, NEAT, ...
