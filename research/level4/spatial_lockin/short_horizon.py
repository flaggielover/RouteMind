from __future__ import annotations

from typing import cast

from .linalg import Vector, scale_vector, vector
from .mechanism import DeliveryMechanism
from .records import Trajectory
from .reduced_model import ReducedModel


def _list_value(payload: dict[str, object], name: str) -> list[object]:
    value = payload.get(name)
    if not isinstance(value, list):
        raise TypeError(f"{name} must be a list")
    return value


def _number(payload: dict[str, object], name: str) -> float:
    value = payload.get(name)
    if isinstance(value, bool) or not isinstance(value, (float, int)):
        raise TypeError(f"{name} must be numeric")
    return float(value)


def _number_list(payload: dict[str, object], name: str) -> tuple[float, ...]:
    result: list[float] = []
    for value in _list_value(payload, name):
        if isinstance(value, bool) or not isinstance(value, (float, int)):
            raise TypeError(f"{name} values must be numeric")
        result.append(float(value))
    return tuple(result)


def _integer_list(payload: dict[str, object], name: str) -> tuple[int, ...]:
    result: list[int] = []
    for value in _list_value(payload, name):
        if isinstance(value, bool) or not isinstance(value, int):
            raise TypeError(f"{name} values must be integers")
        result.append(value)
    return tuple(result)


def _directions(payload: dict[str, object]) -> tuple[tuple[str, Vector], ...]:
    raw = _list_value(payload, "perturbation_directions")
    return tuple((f"d{index:02d}", vector(item)) for index, item in enumerate(raw))


def generate_short_horizon(
    preregistration: dict[str, object], *, diagnostic: bool = False
) -> tuple[tuple[Trajectory, ...], tuple[Trajectory, ...]]:
    identification = preregistration["identification"]
    if not isinstance(identification, dict):
        raise TypeError("identification configuration is invalid")
    layer_r_payload = preregistration["layer_r"]
    layer_m_payload = preregistration["layer_m"]
    if not isinstance(layer_r_payload, dict) or not isinstance(layer_m_payload, dict):
        raise TypeError("model configuration is invalid")
    typed_r = cast(dict[str, object], layer_r_payload)
    typed_m = cast(dict[str, object], layer_m_payload)
    seeds = _integer_list(identification, "seeds")
    if diagnostic:
        seeds = seeds[:4]
    magnitudes = _number_list(identification, "perturbation_magnitudes")
    alphas = _number_list(identification, "feedback_settings")
    horizon = int(_number(identification, "horizon"))
    reduced = ReducedModel.from_config(typed_r)
    mechanism = DeliveryMechanism.from_config(typed_m)
    layer_r: list[Trajectory] = []
    layer_m: list[Trajectory] = []
    for alpha in alphas:
        for magnitude in magnitudes:
            for direction_id, direction in _directions(identification):
                initial = scale_vector(direction, magnitude)
                for seed in seeds:
                    stream_seed = (
                        seed
                        + int(alpha * 1000) * 100_000
                        + int(magnitude * 1000) * 10_000
                        + int(direction_id[1:]) * 100
                    )
                    reduced_run = reduced.simulate(
                        initial,
                        alpha,
                        horizon,
                        stream_seed,
                        _number(identification, "layer_r_noise_sd"),
                        magnitude=magnitude,
                        direction_id=direction_id,
                    )
                    layer_r.append(
                        Trajectory(
                            reduced_run.layer,
                            reduced_run.alpha,
                            reduced_run.magnitude,
                            reduced_run.direction_id,
                            seed,
                            reduced_run.states,
                        )
                    )
                    mechanism_run = mechanism.simulate(
                        initial,
                        alpha,
                        horizon,
                        stream_seed,
                        _number(identification, "layer_m_noise_sd"),
                    )
                    layer_m.append(
                        Trajectory(
                            "M",
                            alpha,
                            magnitude,
                            direction_id,
                            seed,
                            mechanism_run.observations,
                        )
                    )
    return tuple(layer_r), tuple(layer_m)
