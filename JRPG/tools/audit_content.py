"""Contrôler les quantités MVP et l'accès effectif au contenu embarqué."""

import json

from JRPG.domain.dialogues import StoryOperation
from JRPG.domain.quests import QuestKind
from JRPG.domain.world import ObjectKind
from JRPG.infrastructure.combat_content import load_combat_catalog
from JRPG.infrastructure.world_content import create_exploration_session


def main() -> None:
    catalog = load_combat_catalog()
    session = create_exploration_session()
    story = session.story
    assert story is not None
    objects = tuple(entry for area in session.world.maps for entry in area.objects)
    profiles = {profile.id: profile for profile in catalog.profiles}
    boss_ids = {identity for identity, profile in catalog.enemy_profiles if profiles[profile].boss}
    hero_skills = {skill for hero in catalog.heroes for skill in hero.skills}
    used_skills = hero_skills | {skill for enemy in catalog.enemies for skill in enemy.skills}
    placed_enemies = {identity for entry in objects for identity in entry.enemies}
    obtainable = (
        {offer.item.id for shop in story.content.shops for offer in shop.offers}
        | {stack.item.id for quest in story.content.quests for stack in quest.reward.items}
        | {stack.item.id for obj in objects for stack in obj.items}
        | {stack.item.id for stack in catalog.initial_items}
        | {item.id for hero in session.party.members for _, item in hero.equipment}
    )
    accepted = {
        effect.reference
        for dialogue in story.content.dialogues
        for node in dialogue.nodes
        for choice in node.choices
        for effect in choice.effects
        if effect.operation == StoryOperation.ACCEPT_QUEST
    }
    claimed = {
        effect.reference
        for dialogue in story.content.dialogues
        for node in dialogue.nodes
        for choice in node.choices
        for effect in choice.effects
        if effect.operation == StoryOperation.CLAIM_QUEST
    }
    counts = dict(
        heroes=len(catalog.heroes),
        classes=len({hero.definition.character_class.id for hero in catalog.heroes}),
        active_party=len(session.party.members),
        maps=len(session.world.maps),
        enemy_types=len(catalog.enemies) - len(boss_ids),
        bosses=len(boss_ids),
        hero_skills=len(hero_skills),
        items=len(story.content.items),
        equipment=sum(bool(item.slots) for item in story.content.items),
        main_quests=sum(quest.kind == QuestKind.MAIN for quest in story.content.quests),
        side_quests=sum(quest.kind == QuestKind.SIDE for quest in story.content.quests),
        npcs=sum(obj.kind == ObjectKind.NPC for obj in objects),
    )
    minimum = dict(
        heroes=4,
        classes=4,
        active_party=4,
        maps=3,
        enemy_types=5,
        bosses=1,
        hero_skills=12,
        items=15,
        equipment=10,
        main_quests=1,
        side_quests=3,
        npcs=5,
    )
    assert all(counts[key] >= value for key, value in minimum.items()), counts
    assert placed_enemies == {enemy.id for enemy in catalog.enemies}
    assert used_skills == {ability.id for ability in catalog.abilities}
    assert obtainable == {item.id for item in story.content.items}
    assert accepted == claimed == {quest.id for quest in story.content.quests}
    assert {obj.id for obj in objects if obj.kind == ObjectKind.NPC} == dict(
        story.content.npc_dialogues
    ).keys()
    print(json.dumps(counts, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
