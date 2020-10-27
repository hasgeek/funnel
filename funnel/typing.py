from typing import List, Optional, Set, Tuple, TypeVar, Union

#: Type used to indicate that a decorator returns its decorated attribute
T = TypeVar('T')

#: Return type of the `migrate_user` and `migrate_profile` methods
OptionalMigratedTables = Optional[Union[List[str], Tuple[str], Set[str]]]
