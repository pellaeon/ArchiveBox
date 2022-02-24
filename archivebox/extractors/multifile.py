__package__ = 'archivebox.extractors'

from pathlib import Path

from typing import Optional
import json

from ..index.schema import Link, ArchiveResult, ArchiveError
from ..system import run, chmod_file
from ..util import (
    enforce_types,
    is_static_file,
    chrome_args,
)
from ..config import (
    TIMEOUT,
    SAVE_MULTIFILE,
    DEPENDENCIES,
    MULTIFILE_VERSION,
)
from ..logging_util import TimedProgress


@enforce_types
def should_save_multifile(link: Link, out_dir: Optional[Path]=None, overwrite: Optional[bool]=False) -> bool:
    if is_static_file(link.url):
        return False

    out_dir = out_dir or Path(link.link_dir)
    if not overwrite and (out_dir / 'multifile').exists():
        return False

    return SAVE_MULTIFILE


@enforce_types
def save_multifile(link: Link, out_dir: Optional[Path]=None, timeout: int=TIMEOUT) -> ArchiveResult:
    """
    The `multifile` CLI outputs a directory (whose name is controlled by the `--output-directory` arg)
    containing a main html file (whose name is controlled by the 2nd positional argument (`output` here)).
    """

    out_dir = out_dir or Path(link.link_dir)
    output = "index.html"

    # FIXME multifile CLI uses Firefox, so chrome args are ignored so far
    browser_args = chrome_args(TIMEOUT=0)

    cmd = [
        DEPENDENCIES['MULTIFILE_BINARY']['path'],
        '--output-directory={}'.format("multifile"),
        link.url,
        output,
    ]

    status = 'succeeded'
    timer = TimedProgress(timeout, prefix='      ')
    try:
        result = run(cmd, cwd=str(out_dir), timeout=timeout)

        # parse out number of files downloaded from last line of stderr:
        #  "Downloaded: 76 files, 4.0M in 1.6s (2.52 MB/s)"
        output_tail = [
            line.strip()
            for line in (result.stdout + result.stderr).decode().rsplit('\n', 3)[-3:]
            if line.strip()
        ]
        hints = (
            'Got multifile response code: {}.'.format(result.returncode),
            *output_tail,
        )

        # Check for common failure cases
        if (result.returncode > 0) or not Path(out_dir,'multifile',output).is_file():
            raise ArchiveError('MultiFile was not able to archive the page', hints)
    except (Exception, OSError) as err:
        status = 'failed'
        output = err
    finally:
        timer.end()

    return ArchiveResult(
        cmd=cmd,
        pwd=str(out_dir),
        cmd_version=MULTIFILE_VERSION,
        output=output,
        status=status,
        **timer.stats,
    )
