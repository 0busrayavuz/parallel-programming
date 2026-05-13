# Entry shim: run the package CLI as before: python parallel_video.py ...
# Prefer: python -m rt_edge_live

from rt_edge_live.cli import main

if __name__ == "__main__":
    main()
