from __future__ import annotations

import argparse
from pathlib import Path

from . import data, fieldlines, lto, pic, pic_model, pic_tiles, pic_validation, poincare


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="viz",
        description="Figures of the BS-SOLCTRA field-line simulation.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    starts = sub.add_parser(
        "starts", help="write a radial starting-point file for the simulation"
    )
    starts.add_argument("--out", type=Path, required=True)
    starts.add_argument("--count", type=int, required=True)
    starts.add_argument("--r-min", type=float, default=0.195)
    starts.add_argument("--r-max", type=float, default=0.312)

    section = sub.add_parser("poincare", help="Poincare section of the traced lines")
    section.add_argument("--data", type=Path, required=True)
    section.add_argument("--out", type=Path, required=True)
    section.add_argument("--phi-label", default=r"$\varphi = 0$")
    section.add_argument("--show-boundary", action="store_true")

    confinement = sub.add_parser(
        "confinement", help="traced arc length against starting radius"
    )
    confinement.add_argument("--data", type=Path, required=True)
    confinement.add_argument("--out", type=Path, required=True)
    confinement.add_argument("--step-size", type=float, default=0.001)

    three_d = sub.add_parser("fieldlines", help="3D coils and field lines")
    three_d.add_argument("--data", type=Path, required=True)
    three_d.add_argument("--resources", type=Path, required=True)
    three_d.add_argument("--out", type=Path, required=True)
    three_d.add_argument("--colour-by", choices=["field", "radius"], default="field")
    three_d.add_argument("--max-lines", type=int, default=None)
    three_d.add_argument("--zoom", type=float, default=1.0)
    three_d.add_argument("--azimuth", type=float, default=55.0)
    three_d.add_argument("--elevation", type=float, default=22.0)
    three_d.add_argument("--max-step", type=int, default=None)
    three_d.add_argument("--line-ids", type=int, nargs="+", default=None)
    three_d.add_argument("--coil-fraction", type=float, default=1.0)
    three_d.add_argument("--coil-opacity", type=float, default=1.0)
    three_d.add_argument("--line-radius", type=float, default=0.0016)
    three_d.add_argument("--distance", type=float, default=1.15)
    three_d.add_argument("--no-scalar-bar", action="store_true")

    migration = sub.add_parser(
        "pic-migration", help="particles migrated per step, by initialization style"
    )
    migration.add_argument("--data", type=Path, required=True)
    migration.add_argument("--out", type=Path, required=True)
    migration.add_argument("--ranks", type=int, default=8)

    versus = sub.add_parser(
        "pic-mape", help="migration rate against MAPE, one point per style and scaling"
    )
    versus.add_argument("--data", type=Path, required=True)
    versus.add_argument("--out", type=Path, required=True)
    versus.add_argument("--node-counts", type=int, nargs="+", default=None)
    versus.add_argument("--per-rank", action="store_true")

    table = sub.add_parser("pic-summary", help="print the numbers behind the PIC figures")
    table.add_argument("--data", type=Path, required=True)
    table.add_argument("--node-counts", type=int, nargs="+", default=None)

    model = sub.add_parser("pic-model", help="charge mesh, force stencil and particle tracks")
    model.add_argument("--data", type=Path, required=True)
    model.add_argument("--out", type=Path, required=True)
    model.add_argument("--grid-size", type=float, default=24.0)
    model.add_argument("--lines", type=int, default=5)
    model.add_argument("--prefix", default="t")

    tiles = sub.add_parser("pic-tiles", help="rank tiles with the particles that migrated")
    tiles.add_argument("--data", type=Path, required=True)
    tiles.add_argument("--out", type=Path, required=True)
    tiles.add_argument("--prefix", default="p")
    tiles.add_argument("--grid-size", type=float, default=1000.0)
    tiles.add_argument("--first-step", type=int, default=0)
    tiles.add_argument("--last-step", type=int, default=None)
    tiles.add_argument("--mark-since", type=int, default=None)

    validation = sub.add_parser(
        "pic-validation", help="simulated against analytic position, C and Rust"
    )
    validation.add_argument("--data", type=Path, required=True)
    validation.add_argument("--out", type=Path, required=True)
    validation.add_argument("--grid-size", type=float, default=200.0)
    validation.add_argument("--tracks", type=int, default=3)

    lto_cmd = sub.add_parser(
        "lto", help="PIC and BS-SOLCTRA with and without LTO on both sides"
    )
    lto_cmd.add_argument("--results", type=Path, required=True)
    lto_cmd.add_argument("--out-dir", type=Path, required=True)
    lto_cmd.add_argument("--summary", action="store_true")

    args = parser.parse_args(argv)

    if args.command == "starts":
        path = data.write_radial_starts(
            args.out, args.count, args.r_min, args.r_max
        )
        print(f"wrote {args.count} starting points to {path}")
    elif args.command == "poincare":
        print(
            f"wrote {poincare.plot(args.data, args.out, args.phi_label, args.show_boundary)}"
        )
    elif args.command == "confinement":
        print(
            f"wrote {poincare.plot_confinement(args.data, args.out, args.step_size)}"
        )
    elif args.command == "fieldlines":
        path = fieldlines.render(
            args.data,
            args.resources,
            args.out,
            colour_by=args.colour_by,
            max_step=args.max_step,
            max_lines=args.max_lines,
            line_ids=args.line_ids,
            coil_fraction=args.coil_fraction,
            coil_opacity=args.coil_opacity,
            line_radius=args.line_radius,
            zoom=args.zoom,
            azimuth=args.azimuth,
            elevation=args.elevation,
            distance=args.distance,
            show_scalar_bar=not args.no_scalar_bar,
        )
        print(f"wrote {path}")
    elif args.command == "lto":
        if args.summary:
            lto.print_summary(args.results)
        for path in lto.render_all(args.results, args.out_dir):
            print(f"wrote {path}")
    elif args.command == "pic-migration":
        print(f"wrote {pic.plot_per_step(args.data, args.out, args.ranks)}")
    elif args.command == "pic-mape":
        print(
            f"wrote {pic.plot_migration_vs_mape(args.data, args.out, args.node_counts, args.per_rank)}"
        )
    elif args.command == "pic-model":
        print(
            f"wrote {pic_model.plot(args.data, args.out, args.grid_size, args.lines, args.prefix)}"
        )
    elif args.command == "pic-tiles":
        print(
            f"wrote {pic_tiles.plot(args.data, args.out, args.prefix, args.first_step, args.last_step, args.mark_since, args.grid_size)}"
        )
    elif args.command == "pic-validation":
        print(
            f"wrote {pic_validation.plot(args.data, args.out, args.grid_size, n_tracks=args.tracks)}"
        )
    elif args.command == "pic-summary":
        print(pic.summary(args.data, args.node_counts).to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
