from twitter_ops_agent.cli import build_parser


def test_cli_parser_accepts_run_v2():
    parser = build_parser()
    args = parser.parse_args(["run-v2"])
    assert args.command == "run-v2"
