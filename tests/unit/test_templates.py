"""Reaction templates (T048): only {session}, {tool}, {summary} are filled; nothing is evaluated."""

from __future__ import annotations

from aibuddy.hats.templates import render


def test_known_placeholders_are_filled():
    out = render("Segfault in {session} running {tool}: {summary}",
                 session="demo", tool="Bash", summary="npm test")
    assert out == "Segfault in demo running Bash: npm test"


def test_unknown_placeholders_are_left_as_literal_text():
    assert render("hello {name}", session="s", tool="t", summary="u") == "hello {name}"


def test_attribute_and_index_access_is_not_evaluated():
    out = render("{session.__class__} {0} {summary[0]}", session="s", tool="t", summary="abc")
    assert out == "{session.__class__} {0} {summary[0]}"


def test_braces_without_names_are_untouched():
    assert render("{} {{ }}", session="s", tool="t", summary="u") == "{} {{ }}"


def test_output_is_capped_for_the_device():
    out = render("{summary}", session="s", tool="t", summary="x" * 1000)
    assert len(out) <= 200
