import asyncio
import json
import os
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import httpx

from core.config import BASE_DIR, ENV_FILE, invalidate_balance_cache, is_valid_secret

KEYS_FILE = BASE_DIR / "keys.json"
_pool_lock = asyncio.Lock()


def _mask_secret(secret: str) -> str:
    if not secret:
        return ""
    if len(secret) > 10:
        return f"{secret[:6]}...{secret[-4:]}"
    return "***"


@dataclass
class KeyPair:
    id: str
    label: str
    api_key: str
    admin_key: str
    provider: str = "abliteration"
    base_url: str = "https://api.abliteration.ai/v1"
    balance: Optional[float] = None
    status: str = "standby"  # "active", "standby", "exhausted", "error"
    last_checked: float = 0.0
    error_message: Optional[str] = None
    created_at: float = field(default_factory=time.time)

    @property
    def masked_api_key(self) -> str:
        return _mask_secret(self.api_key)

    @property
    def masked_admin_key(self) -> str:
        return _mask_secret(self.admin_key)

    @property
    def formatted_balance(self) -> str:
        return f"${self.balance:.4f}" if self.balance is not None else "Не проверен"

    def to_dict(self, include_secrets: bool = False) -> Dict[str, Any]:
        d = {
            "id": self.id,
            "label": self.label,
            "provider": self.provider,
            "base_url": self.base_url,
            "balance": self.balance,
            "formatted_balance": f"${self.balance:.4f}" if self.balance is not None else "Не проверен",
            "status": self.status,
            "last_checked": self.last_checked,
            "error_message": self.error_message,
            "created_at": self.created_at,
            "masked_api_key": _mask_secret(self.api_key),
            "masked_admin_key": _mask_secret(self.admin_key),
            "has_api_key": bool(self.api_key),
            "has_admin_key": bool(self.admin_key),
        }
        if include_secrets:
            d["api_key"] = self.api_key
            d["admin_key"] = self.admin_key
        return d


class KeyPoolManager:
    def __init__(self, storage_path: Path = KEYS_FILE):
        self.storage_path = storage_path
        self.auto_rotate: bool = True
        self.auto_purge_exhausted: bool = True  # По умолчанию удалять с балансом $0
        self.active_pair_id: Optional[str] = None
        self.pairs: Dict[str, KeyPair] = {}
        self._loaded: bool = False

    def _sync_to_env(self, pair: Optional[KeyPair]) -> None:
        """Синхронизирует активную пару в .env для совместимости."""
        if not pair:
            return
        try:
            from core.config import _read_raw_env
            env_vars = _read_raw_env()
            if pair.provider == "openrouter":
                env_vars["OPENROUTER_API_KEY"] = pair.api_key
                env_vars["ABLIT_KEY"] = ""
            else:
                env_vars["ABLIT_KEY"] = pair.api_key
                env_vars["OPENROUTER_API_KEY"] = ""

            env_vars["ADMIN_KEY"] = pair.admin_key
            env_vars["BASE_URL"] = pair.base_url

            lines = [
                f"BASE_URL={env_vars.get('BASE_URL', 'https://api.abliteration.ai/v1')}",
                f"ABLIT_KEY={env_vars.get('ABLIT_KEY', '')}",
                f"OPENROUTER_API_KEY={env_vars.get('OPENROUTER_API_KEY', '')}",
                f"ADMIN_KEY={env_vars.get('ADMIN_KEY', '')}",
                f"DISTILL_ENGINE={env_vars.get('DISTILL_ENGINE', 'gemini_free')}",
                f"GEMINI_API_KEY={env_vars.get('GEMINI_API_KEY', '')}",
                f"PORT={env_vars.get('PORT', '5051')}",
            ]
            tmp_env = ENV_FILE.with_suffix(".env.tmp")
            tmp_env.write_text("\n".join(lines) + "\n", encoding="utf-8")
            os.replace(tmp_env, ENV_FILE)
            if os.name != "nt":
                try:
                    os.chmod(ENV_FILE, 0o600)
                except OSError:
                    pass

            os.environ["BASE_URL"] = pair.base_url
            if pair.provider == "openrouter":
                os.environ["OPENROUTER_API_KEY"] = pair.api_key
                os.environ["ABLIT_KEY"] = ""
            else:
                os.environ["ABLIT_KEY"] = pair.api_key
                os.environ["OPENROUTER_API_KEY"] = ""
            os.environ["ADMIN_KEY"] = pair.admin_key
            invalidate_balance_cache()
        except Exception as e:
            print(f"[KeyPool] Ошибка синхронизации в .env: {e}")

    def _save_unlocked(self) -> None:
        data = {
            "version": 1,
            "auto_rotate": self.auto_rotate,
            "auto_purge_exhausted": self.auto_purge_exhausted,
            "active_pair_id": self.active_pair_id,
            "pairs": [p.to_dict(include_secrets=True) for p in self.pairs.values()],
        }
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_file = self.storage_path.with_suffix(".json.tmp")
        tmp_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(tmp_file, self.storage_path)
        if os.name != "nt":
            try:
                os.chmod(self.storage_path, 0o600)
            except OSError:
                pass

    def _load_unlocked(self) -> None:
        if self._loaded:
            return
        self.pairs.clear()

        if self.storage_path.exists():
            try:
                raw = json.loads(self.storage_path.read_text(encoding="utf-8"))
                self.auto_rotate = bool(raw.get("auto_rotate", True))
                self.auto_purge_exhausted = bool(raw.get("auto_purge_exhausted", True))
                self.active_pair_id = raw.get("active_pair_id")

                for item in raw.get("pairs", []):
                    pair = KeyPair(
                        id=item["id"],
                        label=item.get("label") or f"Аккаунт {item['id'][:4]}",
                        api_key=item.get("api_key", ""),
                        admin_key=item.get("admin_key", ""),
                        provider=item.get("provider", "abliteration"),
                        base_url=item.get("base_url", "https://api.abliteration.ai/v1"),
                        balance=item.get("balance"),
                        status=item.get("status", "standby"),
                        last_checked=float(item.get("last_checked", 0.0)),
                        error_message=item.get("error_message"),
                        created_at=float(item.get("created_at", time.time())),
                    )
                    self.pairs[pair.id] = pair
                self._loaded = True
            except Exception as e:
                print(f"[KeyPool] Ошибка загрузки {self.storage_path}: {e}")

        # Если файл пуст или отсутствует — импортируем из .env
        if not self.pairs:
            try:
                from core.config import load_config
                cfg = load_config()
                if cfg.get("has_key"):
                    initial_id = "pair_" + uuid.uuid4().hex[:8]
                    initial_pair = KeyPair(
                        id=initial_id,
                        label="Основной аккаунт",
                        api_key=cfg.get("api_key", ""),
                        admin_key=cfg.get("admin_key", ""),
                        provider=cfg.get("provider", "abliteration"),
                        base_url=cfg.get("base_url", "https://api.abliteration.ai/v1"),
                        status="active",
                        created_at=time.time(),
                    )
                    self.pairs[initial_id] = initial_pair
                    self.active_pair_id = initial_id
                    self._save_unlocked()
            except Exception as e:
                print(f"[KeyPool] Ошибка инициализации из .env: {e}")

        # Убедимся, что есть ровно одна активная пара
        active = self.pairs.get(self.active_pair_id) if self.active_pair_id else None
        if not active and self.pairs:
            # Находим первую не исчерпанную
            for p in self.pairs.values():
                if p.status != "exhausted":
                    p.status = "active"
                    self.active_pair_id = p.id
                    active = p
                    break
            if not active:
                first = next(iter(self.pairs.values()))
                first.status = "active"
                self.active_pair_id = first.id
                active = first
            self._save_unlocked()

        self._loaded = True

    async def get_active_pair(self) -> Optional[KeyPair]:
        async with _pool_lock:
            self._load_unlocked()
            if self.active_pair_id and self.active_pair_id in self.pairs:
                return self.pairs[self.active_pair_id]
            for p in self.pairs.values():
                if p.status == "active":
                    self.active_pair_id = p.id
                    return p
            return None

    async def get_all_pairs(self) -> List[KeyPair]:
        async with _pool_lock:
            self._load_unlocked()
            return list(self.pairs.values())

    async def get_status_payload(self) -> Dict[str, Any]:
        async with _pool_lock:
            self._load_unlocked()
            active_pair = self.pairs.get(self.active_pair_id) if self.active_pair_id else None
            pairs_list = [p.to_dict(include_secrets=False) for p in self.pairs.values()]
            # Сортируем: активный первый, затем по дате добавления
            pairs_list.sort(key=lambda x: (0 if x["id"] == self.active_pair_id else 1, -x["created_at"]))

            positive_count = sum(1 for p in self.pairs.values() if p.balance is not None and p.balance > 0 and p.status != "exhausted")
            return {
                "auto_rotate": self.auto_rotate,
                "auto_purge_exhausted": self.auto_purge_exhausted,
                "active_pair_id": self.active_pair_id,
                "active_pair": active_pair.to_dict(include_secrets=False) if active_pair else None,
                "total_pairs": len(self.pairs),
                "ready_pairs_count": positive_count,
                "pairs": pairs_list,
            }

    async def update_settings(self, auto_rotate: Optional[bool] = None, auto_purge_exhausted: Optional[bool] = None) -> Dict[str, Any]:
        async with _pool_lock:
            self._load_unlocked()
            if auto_rotate is not None:
                self.auto_rotate = bool(auto_rotate)
            if auto_purge_exhausted is not None:
                self.auto_purge_exhausted = bool(auto_purge_exhausted)
            self._save_unlocked()
        return await self.get_status_payload()

    async def add_pair(
        self,
        api_key: str,
        admin_key: str,
        label: Optional[str] = None,
        provider: str = "abliteration",
        base_url: Optional[str] = None,
    ) -> KeyPair:
        api_k = api_key.strip()
        admin_k = admin_key.strip()
        if not is_valid_secret(api_k):
            raise ValueError("Некорректный или пустой основной API-ключ")
        if not is_valid_secret(admin_k):
            raise ValueError("Некорректный или пустой Admin Key")

        prov = provider.strip().lower() if provider else "abliteration"
        b_url = (base_url or ("https://api.abliteration.ai/v1" if prov == "abliteration" else "https://openrouter.ai/api/v1")).rstrip("/")

        async with _pool_lock:
            self._load_unlocked()
            # Проверим, нет ли уже такого ключа
            for p in self.pairs.values():
                if p.api_key == api_k:
                    raise ValueError(f"Этот API-ключ уже добавлен в пул ({p.label})")

            pair_id = "pair_" + uuid.uuid4().hex[:8]
            lbl = label.strip() if label and label.strip() else f"Аккаунт {len(self.pairs) + 1}"

            new_pair = KeyPair(
                id=pair_id,
                label=lbl,
                api_key=api_k,
                admin_key=admin_k,
                provider=prov,
                base_url=b_url,
                status="standby",
                created_at=time.time(),
            )

            # Проверим баланс сразу при добавлении
            bal, err = await self._check_balance_for_pair(new_pair)
            new_pair.balance = bal
            new_pair.error_message = err
            new_pair.last_checked = time.time()

            if bal is not None and bal <= 0.0:
                new_pair.status = "exhausted"

            # Если нет активной пары или активная исчерпана — активируем новую, если у неё есть баланс
            active = self.pairs.get(self.active_pair_id) if self.active_pair_id else None
            active_is_dead = not active or active.status == "exhausted" or (active.balance is not None and active.balance <= 0)

            if active_is_dead and (bal is None or bal > 0.0):
                new_pair.status = "active"
                if active:
                    active.status = "standby" if (active.balance is not None and active.balance > 0) else "exhausted"
                self.active_pair_id = new_pair.id
                self._sync_to_env(new_pair)

            self.pairs[new_pair.id] = new_pair
            self._save_unlocked()

            return new_pair

    async def remove_pair(self, pair_id: str) -> bool:
        async with _pool_lock:
            self._load_unlocked()
            if pair_id not in self.pairs:
                return False

            del self.pairs[pair_id]

            if self.active_pair_id == pair_id:
                self.active_pair_id = None
                # Ищем следующего кандидата
                for p in self.pairs.values():
                    if p.status != "exhausted":
                        p.status = "active"
                        self.active_pair_id = p.id
                        self._sync_to_env(p)
                        break

            self._save_unlocked()
            return True

    async def set_active_pair(self, pair_id: str) -> KeyPair:
        async with _pool_lock:
            self._load_unlocked()
            if pair_id not in self.pairs:
                raise ValueError("Пара ключей не найдена")

            for p in self.pairs.values():
                if p.id == pair_id:
                    p.status = "active"
                    self.active_pair_id = p.id
                    self._sync_to_env(p)
                elif p.status == "active":
                    p.status = "standby" if (p.balance is None or p.balance > 0) else "exhausted"

            self._save_unlocked()
            return self.pairs[pair_id]

    async def purge_exhausted_pairs(self) -> int:
        """Удаляет все пары с балансом $0 или статусом exhausted."""
        async with _pool_lock:
            self._load_unlocked()
            to_remove = [
                pid for pid, p in self.pairs.items()
                if p.status == "exhausted" or (p.balance is not None and p.balance <= 0.0)
            ]
            count = 0
            for pid in to_remove:
                del self.pairs[pid]
                count += 1
                if self.active_pair_id == pid:
                    self.active_pair_id = None

            if not self.active_pair_id and self.pairs:
                first = next(iter(self.pairs.values()))
                first.status = "active"
                self.active_pair_id = first.id
                self._sync_to_env(first)

            self._save_unlocked()
            return count

    async def _check_balance_for_pair(self, pair: KeyPair) -> Tuple[Optional[float], Optional[str]]:
        """Запрашивает актуальный баланс пары через её admin_key или api_key."""
        try:
            async with httpx.AsyncClient(timeout=8.0) as http:
                if pair.provider == "openrouter":
                    resp = await http.get(
                        "https://openrouter.ai/api/v1/credits",
                        headers={"Authorization": f"Bearer {pair.api_key}"},
                    )
                    if resp.status_code == 200:
                        d = resp.json().get("data", {})
                        tot = float(d.get("total_credits", 0))
                        usage = float(d.get("total_usage", 0))
                        rem = max(0.0, tot - usage)
                        return (rem, None)
                    return (None, f"HTTP {resp.status_code}: {resp.text[:100]}")
                else:
                    # Abliteration / Custom
                    admin_k = pair.admin_key or pair.api_key
                    resp = await http.get(
                        "https://api.abliteration.ai/v1/organization/balance",
                        headers={"Authorization": f"Bearer {admin_k}"},
                    )
                    if resp.status_code == 200:
                        avail = float(resp.json().get("available_usd", 0.0))
                        return (avail, None)
                    return (None, f"HTTP {resp.status_code}: {resp.text[:100]}")
        except Exception as e:
            return (None, str(e))

    async def check_all_balances(self) -> Dict[str, Any]:
        """Опрашивает балансы всех пар в пуле и применяет правила авто-удаления/ротации."""
        async with _pool_lock:
            self._load_unlocked()
            all_pairs = list(self.pairs.values())

        async def _check_one(p: KeyPair):
            bal, err = await self._check_balance_for_pair(p)
            return p.id, bal, err

        results = await asyncio.gather(*[_check_one(p) for p in all_pairs], return_exceptions=True)

        async with _pool_lock:
            for res in results:
                if isinstance(res, tuple):
                    pid, bal, err = res
                    if pid in self.pairs:
                        p = self.pairs[pid]
                        p.last_checked = time.time()
                        if bal is not None:
                            p.balance = bal
                            p.error_message = None
                            if bal <= 0.0:
                                p.status = "exhausted"
                            elif p.status == "exhausted":
                                p.status = "standby"
                        else:
                            p.error_message = err

            # Авто-удаление исчерпанных, если включено
            if self.auto_purge_exhausted:
                to_del = [
                    pid for pid, p in self.pairs.items()
                    if p.status == "exhausted" or (p.balance is not None and p.balance <= 0.0)
                ]
                for pid in to_del:
                    del self.pairs[pid]
                    if self.active_pair_id == pid:
                        self.active_pair_id = None

            # Если активный ключ стал пустым или был удален — ротируем на следующий
            active = self.pairs.get(self.active_pair_id) if self.active_pair_id else None
            if not active or active.status == "exhausted" or (active.balance is not None and active.balance <= 0):
                next_cand = None
                for p in self.pairs.values():
                    if p.status != "exhausted" and (p.balance is None or p.balance > 0):
                        next_cand = p
                        break
                if next_cand:
                    next_cand.status = "active"
                    self.active_pair_id = next_cand.id
                    self._sync_to_env(next_cand)

            self._save_unlocked()

        return await self.get_status_payload()

    async def rotate_to_next_active(self, reason: str = "") -> Optional[KeyPair]:
        """
        Переключает активный ключ на следующий доступный с положительным балансом.
        Если auto_purge_exhausted == True, нулевой ключ сразу удаляется.
        """
        async with _pool_lock:
            self._load_unlocked()

            current_id = self.active_pair_id
            current_pair = self.pairs.get(current_id) if current_id else None

            print(f"[KeyPool] Ротация ключа (текущий: {current_pair.label if current_pair else 'None'}). Причина: {reason}")

            if current_pair:
                current_pair.balance = 0.0
                current_pair.status = "exhausted"
                current_pair.error_message = reason or "Баланс исчерпан ($0.00)"

                if self.auto_purge_exhausted:
                    print(f"[KeyPool] Авто-удаление исчерпанного ключа: {current_pair.label} ({current_pair.id})")
                    del self.pairs[current_id]
                    self.active_pair_id = None

            # Ищем кандидата среди оставшихся пар
            candidate: Optional[KeyPair] = None
            for p in self.pairs.values():
                if p.id != current_id and p.status != "exhausted":
                    candidate = p
                    break

            if not candidate:
                print("[KeyPool] Все ключи в пуле исчерпаны!")
                self.active_pair_id = None
                self._save_unlocked()
                return None

            # Проверим баланс кандидата
            bal, err = await self._check_balance_for_pair(candidate)
            candidate.balance = bal
            candidate.last_checked = time.time()

            if bal is not None and bal <= 0.0:
                candidate.status = "exhausted"
                if self.auto_purge_exhausted:
                    del self.pairs[candidate.id]
                self._save_unlocked()
                # Рекурсивно пробуем следующего
                return await self.rotate_to_next_active(reason="Кандидат имел нулевой баланс")

            candidate.status = "active"
            self.active_pair_id = candidate.id
            self._sync_to_env(candidate)
            self._save_unlocked()

            print(f"[KeyPool] Успешно переключено на {candidate.label} ({candidate.id}), баланс: {candidate.formatted_balance}")
            return candidate


key_pool = KeyPoolManager()


def is_quota_or_balance_error(exc: Exception) -> bool:
    """Определяет, связана ли ошибка запроса с окончанием баланса или квоты."""
    s = str(exc).lower()
    quota_keywords = (
        "insufficient_quota",
        "insufficient_balance",
        "insufficient balance",
        "quota exceeded",
        "exceeded your current quota",
        "billing",
        "payment required",
        "credit",
        "balance",
        "out of credits",
        "402",
    )
    # Исключаем ложные совпадения с балансировкой нагрузки (load balance)
    if "load balance" in s:
        return False
    return any(k in s for k in quota_keywords)
