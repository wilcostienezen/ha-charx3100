"""Thin async Modbus/TCP client and register parsing for the CHARX 3100."""

from __future__ import annotations

import asyncio
import inspect
import logging
from dataclasses import dataclass

from pymodbus.client import AsyncModbusTcpClient
from pymodbus.exceptions import ModbusException

from .const import (
    BLOCK_LENGTH,
    BLOCK_START,
    CP_STRIDE,
    MAX_CHARGING_POINTS,
    OFF_ACTIVE_POWER,
    OFF_APPARENT_POWER,
    OFF_CABLE_CAPACITY,
    OFF_CHARGING_RELEASE,
    OFF_CHARGING_TIME,
    OFF_CONNECTION_TIME,
    OFF_CURRENT_L1,
    OFF_CURRENT_L2,
    OFF_CURRENT_L3,
    OFF_DIGITAL_INPUTS,
    OFF_ENERGY_SESSION,
    OFF_ENERGY_TOTAL,
    OFF_ERROR_CODE,
    OFF_IEC_STATUS,
    OFF_MAX_CURRENT,
    OFF_PWM_CURRENT,
    OFF_PWM_DUTY_CYCLE,
    OFF_REACTIVE_POWER,
    OFF_VOLTAGE_L1,
    OFF_VOLTAGE_L2,
    OFF_VOLTAGE_L3,
    OFF_WATCHDOG_TIMER,
    REG_CHARGING_POINT_COUNT,
)

_LOGGER = logging.getLogger(__name__)


class CharxConnectionError(Exception):
    """Raised when the controller cannot be reached or answers with an error."""


@dataclass
class ChargingPointData:
    """Decoded values of one charging point."""

    number: int
    voltage_l1: float | None
    voltage_l2: float | None
    voltage_l3: float | None
    current_l1: float | None
    current_l2: float | None
    current_l3: float | None
    active_power: float
    reactive_power: float
    apparent_power: float
    energy_total: float
    energy_session: float
    connection_time: int
    charging_time: int
    error_code: int
    digital_inputs: int
    pwm_duty_cycle: int
    pwm_current: int
    cable_capacity: int
    iec_status: str
    charging_release: bool
    max_current: int
    watchdog_timer: int

    @property
    def state_letter(self) -> str | None:
        """Return the IEC 61851-1 state letter (A-F), if known."""
        return self.iec_status[0].upper() if self.iec_status else None


def _u32(regs: list[int], off: int) -> int:
    i = off - BLOCK_START
    return (regs[i] << 16) | regs[i + 1]


def _s32(regs: list[int], off: int) -> int:
    value = _u32(regs, off)
    return value - (1 << 32) if value & 0x80000000 else value


def _u64(regs: list[int], off: int) -> int:
    i = off - BLOCK_START
    return (regs[i] << 48) | (regs[i + 1] << 32) | (regs[i + 2] << 16) | regs[i + 3]


def _u16(regs: list[int], off: int) -> int:
    return regs[off - BLOCK_START]


def _ascii(regs: list[int], off: int, words: int = 1) -> str:
    raw = bytearray()
    for i in range(words):
        word = regs[off - BLOCK_START + i]
        raw += bytes(((word >> 8) & 0xFF, word & 0xFF))
    return raw.replace(b"\x00", b"").decode("ascii", errors="ignore").strip()


def _current(regs: list[int], off: int) -> float | None:
    value = _s32(regs, off)
    return None if value < 0 else value / 1000


def parse_charging_point(number: int, regs: list[int]) -> ChargingPointData:
    """Decode one register block (x232-x308) of a charging point."""
    if len(regs) < BLOCK_LENGTH:
        raise CharxConnectionError(
            f"Charging point {number}: expected {BLOCK_LENGTH} registers, got {len(regs)}"
        )
    return ChargingPointData(
        number=number,
        voltage_l1=_u32(regs, OFF_VOLTAGE_L1) / 1000,
        voltage_l2=_u32(regs, OFF_VOLTAGE_L2) / 1000,
        voltage_l3=_u32(regs, OFF_VOLTAGE_L3) / 1000,
        current_l1=_current(regs, OFF_CURRENT_L1),
        current_l2=_current(regs, OFF_CURRENT_L2),
        current_l3=_current(regs, OFF_CURRENT_L3),
        active_power=_u32(regs, OFF_ACTIVE_POWER) / 1000,
        reactive_power=_s32(regs, OFF_REACTIVE_POWER) / 1000,
        apparent_power=_u32(regs, OFF_APPARENT_POWER) / 1000,
        energy_total=_u64(regs, OFF_ENERGY_TOTAL) / 1000,
        energy_session=_u64(regs, OFF_ENERGY_SESSION) / 1000,
        connection_time=_u32(regs, OFF_CONNECTION_TIME),
        charging_time=_u32(regs, OFF_CHARGING_TIME),
        error_code=_u32(regs, OFF_ERROR_CODE),
        digital_inputs=_u16(regs, OFF_DIGITAL_INPUTS),
        pwm_duty_cycle=_u16(regs, OFF_PWM_DUTY_CYCLE),
        pwm_current=_u16(regs, OFF_PWM_CURRENT),
        cable_capacity=_u16(regs, OFF_CABLE_CAPACITY),
        iec_status=_ascii(regs, OFF_IEC_STATUS),
        charging_release=_u16(regs, OFF_CHARGING_RELEASE) == 1,
        max_current=_u16(regs, OFF_MAX_CURRENT),
        watchdog_timer=_u16(regs, OFF_WATCHDOG_TIMER),
    )


def _unit_keyword() -> str:
    """Return the keyword pymodbus uses for the unit id (renamed in 3.10)."""
    params = inspect.signature(AsyncModbusTcpClient.read_holding_registers).parameters
    return "device_id" if "device_id" in params else "slave"


class CharxModbusClient:
    """Serialises all Modbus traffic to one CHARX 3100 controller."""

    def __init__(self, host: str, port: int, unit_id: int) -> None:
        self.host = host
        self.port = port
        self.unit_id = unit_id
        self._client = AsyncModbusTcpClient(host, port=port, timeout=5, retries=1)
        self._lock = asyncio.Lock()
        self._unit_kw = _unit_keyword()

    async def _ensure_connected(self) -> None:
        if not self._client.connected:
            await self._client.connect()
        if not self._client.connected:
            raise CharxConnectionError(f"Cannot connect to {self.host}:{self.port}")

    async def read(self, address: int, count: int) -> list[int]:
        """Read holding registers (FC03)."""
        async with self._lock:
            await self._ensure_connected()
            try:
                result = await self._client.read_holding_registers(
                    address, count=count, **{self._unit_kw: self.unit_id}
                )
            except (ModbusException, OSError, asyncio.TimeoutError) as err:
                self._client.close()
                raise CharxConnectionError(f"Read {address} failed: {err}") from err
            if result.isError():
                raise CharxConnectionError(f"Read {address} returned {result}")
            return list(result.registers)

    async def write(self, address: int, value: int) -> None:
        """Write one register with FC16.

        The controller answers FC06 with the previous value, so FC16 is used.
        """
        async with self._lock:
            await self._ensure_connected()
            try:
                result = await self._client.write_registers(
                    address, [int(value)], **{self._unit_kw: self.unit_id}
                )
            except (ModbusException, OSError, asyncio.TimeoutError) as err:
                self._client.close()
                raise CharxConnectionError(f"Write {address} failed: {err}") from err
            if result.isError():
                raise CharxConnectionError(f"Write {address}={value} returned {result}")

    async def read_charging_point_count(self) -> int:
        """Return the number of charging points, probing if register 114 is empty."""
        try:
            count = (await self.read(REG_CHARGING_POINT_COUNT, 1))[0]
        except CharxConnectionError:
            count = 0
        if 0 < count <= MAX_CHARGING_POINTS:
            return count
        # Fallback: probe the status register of each possible charging point.
        found = 0
        for number in range(1, MAX_CHARGING_POINTS + 1):
            try:
                await self.read(number * CP_STRIDE + BLOCK_START, 1)
            except CharxConnectionError:
                break
            found = number
        if not found:
            raise CharxConnectionError("No charging points found")
        return found

    async def read_charging_point(self, number: int) -> ChargingPointData:
        """Read and decode one charging point."""
        regs = await self.read(number * CP_STRIDE + BLOCK_START, BLOCK_LENGTH)
        return parse_charging_point(number, regs)

    async def write_charging_release(self, number: int, enabled: bool) -> None:
        """Enable or withdraw the charging release (needs release mode Modbus)."""
        await self.write(number * CP_STRIDE + OFF_CHARGING_RELEASE, 1 if enabled else 0)

    async def write_max_current(self, number: int, amps: int) -> None:
        """Set the maximum charging current in A."""
        await self.write(number * CP_STRIDE + OFF_MAX_CURRENT, amps)

    def close(self) -> None:
        """Close the TCP connection."""
        self._client.close()
