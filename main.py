"""Application entry point for Five Nights at the Boys'."""
import pygame

from game import Game


def main() -> None:
    pygame.init()
    try:
        Game().run()
    finally:
        pygame.quit()


if __name__ == "__main__":
    main()
