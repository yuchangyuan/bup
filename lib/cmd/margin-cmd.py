#!/bin/sh
"""": # -*-python-*-
# https://sourceware.org/bugzilla/show_bug.cgi?id=26034
export "BUP_ARGV_0"="$0"
arg_i=1
for arg in "$@"; do
    export "BUP_ARGV_${arg_i}"="$arg"
    shift
    arg_i=$((arg_i + 1))
done
# Here to end of preamble replaced during install
bup_python="$(dirname "$0")/../../config/bin/python" || exit $?
exec "$bup_python" "$0"
"""
# end of bup preamble

from __future__ import absolute_import
import math, os.path, struct, sys

sys.path[:0] = [os.path.dirname(os.path.realpath(__file__)) + '/..']

from bup import compat, options, git, _helpers
from bup.helpers import log
from bup.io import byte_stream

POPULATION_OF_EARTH=6.7e9  # as of September, 2010

optspec = """
bup margin
--
predict    Guess object offsets and report the maximum deviation
ignore-midx  Don't use midx files; use only plain pack idx files.
"""
o = options.Options(optspec)
opt, flags, extra = o.parse(compat.argv[1:])

_oid_len = 32

if extra:
    o.fatal("no arguments expected")

git.check_repo_or_die()

mi = git.PackIdxList(git.repo(b'objects/pack'), ignore_midx=opt.ignore_midx)

def do_predict(ix, out):
    total = len(ix)
    maxdiff = 0
    for count,i in enumerate(ix):
        prefix = struct.unpack('!Q', i[:8])[0]
        expected = prefix * total // (1 << 64)
        diff = count - expected
        maxdiff = max(maxdiff, abs(diff))
    out.write(b'%d of %d (%.3f%%) '
              % (maxdiff, len(ix), maxdiff * 100.0 / len(ix)))
    out.flush()
    assert(count+1 == len(ix))

sys.stdout.flush()
out = byte_stream(sys.stdout)

if opt.predict:
    if opt.ignore_midx:
        for pack in mi.packs:
            do_predict(pack, out)
    else:
        do_predict(mi, out)
else:
    # default mode: find longest matching prefix
    last = b'\0'*_oid_len
    longmatch = 0
    for i in mi:
        if i == last:
            continue
        #assert(str(i) >= last)
        pm = _helpers.bitmatch(last, i)
        longmatch = max(longmatch, pm)
        last = i
    out.write(b'%d\n' % longmatch)
    log('%d matching prefix bits\n' % longmatch)
    doublings = math.log(len(mi), 2)
    bpd = longmatch / doublings
    log('%.2f bits per doubling\n' % bpd)
    remain = 8 * _oid_len - longmatch
    rdoublings = remain / bpd
    log('%d bits (%.2f doublings) remaining\n' % (remain, rdoublings))
    larger = 2**rdoublings
    log('%g times larger is possible\n' % larger)
    perperson = larger/POPULATION_OF_EARTH
    log('\nEveryone on earth could have %d data sets like yours, all in one\n'
        'repository, and we would expect 1 object collision.\n'
        % int(perperson))
