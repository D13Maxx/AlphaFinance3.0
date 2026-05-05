from dataclasses import dataclass, field
from typing import List, Dict, Any

@dataclass
class Section:
    heading: str
    level: int
    start_line: int
    end_line: int
    subsections: List['Section'] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "heading": self.heading,
            "level": self.level,
            "start_line": self.start_line,
            "end_line": self.end_line,
            "subsections": [sub.to_dict() for sub in self.subsections]
        }

@dataclass
class Document:
    sections: List[Section] = field(default_factory=list)
    lines: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sections": [sect.to_dict() for sect in self.sections],
            # Content is stored in lines, but not duplicated in sections
            "lines": self.lines 
        }
