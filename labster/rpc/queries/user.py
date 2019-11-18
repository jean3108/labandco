from __future__ import annotations

from typing import Any, Dict, List, Optional, Set, Tuple

from werkzeug.exceptions import NotFound

from labster.di import injector
from labster.domain2.model.profile import Profile, ProfileId, ProfileRepository
from labster.domain2.model.structure import Structure, StructureRepository
from labster.domain2.model.type_structure import DE, EQ
from labster.domain2.services.contacts import ContactService
from labster.domain2.services.roles import Role, RoleService
from labster.rpc.registry import context_for
from labster.types import JSON, JSONDict

role_service = injector.get(RoleService)
contact_service = injector.get(ContactService)


@context_for("user")
def get_user(id: str) -> JSONDict:
    profile_repo = injector.get(ProfileRepository)
    structure_repo = injector.get(StructureRepository)

    # TEMP (need refactor)
    user = None
    try:
        old_id = int(id)
        user = profile_repo.get_by_old_id(old_id)
    except (KeyError, ValueError):
        pass

    if not user:
        try:
            user = profile_repo.get_by_id(ProfileId(id))
        except KeyError:
            raise NotFound()

    # /end

    structure_affectation_dto: JSON
    if user.affectation:
        structure_affectation = structure_repo.get_by_dn(user.affectation)
        if structure_affectation:
            structure_affectation_dto = {
                "name": structure_affectation.sigle_ou_nom,
                "id": structure_affectation.id,
            }
        else:
            structure_affectation_dto = None
    else:
        structure_affectation_dto = None

    user_dto = {}
    for k in ["nom", "prenom", "email", "telephone", "uid", "affectation"]:
        user_dto[k] = getattr(user, k)
    # Cas particulier: fonctions est un set() pas une liste.
    user_dto["fonctions"] = sorted(list(user.fonctions))

    roles_dto = get_roles_dto_for_user(user, skip=True)
    perimetre_dto = get_perimetre_dto_for_user(user)

    ctx = {
        "name": user.full_name,
        "user": user_dto,
        "structure_affectation": structure_affectation_dto,
        "roles": roles_dto,
        "perimetre": perimetre_dto,
    }
    return ctx


#
# Serialization helpers
#
def get_roles_dto_for_user(
    user: Profile, base_structure: Optional[Structure] = None, skip: bool = False
) -> List[Dict[str, Any]]:
    roles_for_user = role_service.get_roles_for_user(user)

    all_structures = {}
    for structures in roles_for_user.values():
        for structure in structures:
            all_structures[structure.id] = structure

    list_structures = list(all_structures.values())
    list_structures.sort(key=lambda s: s.depth)

    ancestors: Set[Structure]
    if base_structure:
        ancestors = set(base_structure.ancestors)
    else:
        ancestors = set()

    def get_roles_dto(structure):
        role_list: List[str] = []
        for role, structures in roles_for_user.items():
            if role == Role.MEMBRE:
                continue

            if structure in ancestors:
                continue

            if (
                skip
                and role == Role.MEMBRE_AFFILIE
                and structure.type_name != "Département"
            ):
                continue

            if structure in structures:
                role_list.append(role.value)

        role_list.sort()
        return role_list

    roles_dto = []
    for structure in list_structures:
        role_list = get_roles_dto(structure)
        if not role_list:
            continue

        dto = {
            "structure": {
                "name": structure.sigle_ou_nom,
                "type": structure.type_name,
                "reelle": structure.is_reelle,
                "id": structure.id,
                "depth": structure.depth,
            },
            "roles": role_list,
        }
        roles_dto.append(dto)

    def sorter(dto) -> Tuple[int, int]:
        structure = dto["structure"]
        depth = structure["depth"]
        if set(dto["roles"]) & {
            Role.MEMBRE_AFFECTE.value,
            Role.MEMBRE_RATTACHE.value,
            Role.MEMBRE_AFFILIE.value,
            Role.MEMBRE.value,
            Role.PORTEUR.value,
            Role.SIGNATAIRE.value,
            Role.RESPONSABLE.value,
        }:
            if structure["reelle"]:
                return (1, depth)
            if structure["type"] in {EQ.name, DE.name}:
                return (2, depth)
            return (3, depth)
        if dto["roles"] == Role.GESTIONNAIRE.value:
            return (4, depth)
        if dto["roles"] == Role.ADMIN_LOCAL.value:
            return (5, depth)
        return (6, depth)

    roles_dto.sort(key=sorter)
    return roles_dto


def get_perimetre_dto_for_user(user) -> List[Dict[str, Any]]:
    mapping = contact_service.get_mapping()

    result = []
    for structure, d in mapping.items():
        for contact_type, profile in d.items():
            if profile == user:
                structure_dto = {
                    "name": structure.sigle_ou_nom,
                    "id": structure.id,
                    "type": structure.type_name,
                    "depth": structure.depth,
                }
                dto = {"structure": structure_dto, "types": [contact_type.value]}
                result.append(dto)

    return result