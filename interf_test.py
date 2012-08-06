#!/usr/bin/env python2.7

from random import random, randint
#import os
from pyvows import Vows, expect
import interf  # can this be implicit?


@Vows.create_assertions
def to_be_less_than(topic, expected):
    return topic < expected


class FooError(Exception):
    pass


@Vows.assertion
def not_to_be_an_error_like(topic, expected):
    if isinstance(topic, expected):
        raise Vows.VowsAssertionError('''Expected topic(%s) not to be
                an error of type %s, but it was a %s
                ''', topic, expected, topic.__class__)


# TODO create general 'value at point' test classes, for use in
# specific and random tests
@Vows.batch
class ValueAtPointTests(Vows.Context):
    def topic(self):
        point_test_data = (
            (1.0 / 2, 1.0 / 8, 1.0 / 4, 0.75),
            (1.0 / 3, 3.0 / 5, 1, 0.5),
            (1.0 / 8, 2.0 / 5, 1.0 / 3, 1), )
        base = interf.Base(100, 100, 100, None, None, None)
        for p in point_test_data:
            base.addPoint(*p)
        return base

    def check_some_values(self, topic):
        # manually pre-calculate some values? supply an error as well
        expect(len(topic.points)).to_equal(3)
        expect(interf.value_at_point(topic, 50, 50, 1, 0)).to_equal(
                9.166154761796539e-1)
        expect(interf.value_at_point(topic, 51, 50, 1, 0)).to_equal(
                9.538223520374552e-1)
        expect(interf.value_at_point(topic, 50, 51, 1, 0)).to_equal(
                8.966206758021245e-1)
        expect(interf.value_at_point(topic, 51, 51, 1, 0)).to_equal(
                9.345812279980938e-1)


@Vows.batch
class GeneratePicsFileTest(Vows.Context):
    def topic(self):
        err_file_test_data = [
            (None, AttributeError),
            ('/tmp/nonexistant-directorfoo/foo.foo', IOError), ]
        for td in err_file_test_data:
            excep = None
            try:
                base = interf.Base(100, 100, 100, 3000, td[0], '2')
                # will cause ZeroDivisionError otherwise
                base.addPoint(0, 0, 0, 0)
                interf.generate_pics(base)
            except Exception as ex:
                excep = ex
            yield (excep, td[1])

    def check_topic_error(self, topic):
        expect(topic[0]).to_be_an_error_like(topic[1])
        expect(topic[0]).Not.to_be_an_error_like(FooError)


@Vows.batch
class BaseTests(Vows.Context):
    def topic(self):
        base_test_data = [
            (0, 0, 100, None, None, None),
            (0, 0, 1000, None, None, None), ]
        for item in base_test_data:
            yield interf.Base(*item)

    def resolution_is_10(self, topic):
        if topic.ft == 100:
            expect(topic.resolution).to_equal(10)

    def not_different_if_floats_are_used(self, topic):
        expect(topic.resolution).to_equal(1000.0 / topic.ft)

# A reminder on how to check file contents

#@Vows.batch
#class ReadFile(Vows.Context):
#    def topic(self):
#        return os.path.exists('some_file.txt')
#
#    class AfterSuccessfullyReading(Vows.Context):
#        def topic(self, exists):
#            if exists:
#                return open('some_file.txt').read()
#            return None
#
#        def if_exists_we_can_read_the_contents(self, topic):
#            expect(topic).to_be_like('some string')


@Vows.batch
class PlacTests(Vows.Context):
    # These test are done in plac via the 'Interpreter' class, which
    # seems to be buggy at the moment...
    #def topic(self):
    #    import plac, interf
    #    return interf.generate_pics

    def shows_usage_message(self, topic):
        pass
        #expect(plac.call(topic, ['-h'])).to_be_like('')
        #expect(topic.check(' -h', 'cleared the shelve')).to_be_true()


class PointTests(Vows.Context):
    # TODO nest these tests, matching execution flow.
    def values_at_point_values(self, topic):
        error = 1e-12  # calculate suitable error based on w?
        val = interf.value_at_point(topic[0], topic[1][0], topic[1][1],
                zoom=4, time=10)  # vary zoom and time?
        expect(val).to_be_less_than(error)

    def gen_pmap_values(self, topic):
        # vary zoom and time?
        pmap = interf.gen_pmap(topic[0], zoom=4, time=10)
        val = tuple(pmap[topic[1][0], topic[1][1]])
        expect(val).to_equal((0, 0, 0))


def XRandomPoints(n):
    class XRandomPoints(PointTests):
        def topic(self, base):
            for p in range(n):
                yield (base, (randint(0, base.x - 1), randint(0, base.y - 1)))
    return XRandomPoints


@Vows.batch
class TotalCancellation(Vows.Context):
    '''Tests how classes behave when there are two points that cancel
    each other out.'''  # FIXME Is it alright to put a full-stop here?
    def topic(self):
        x = randint(60, 100)
        y = randint(60, 100)
        w = randint(1, 100)
        p = random()
        gx = random()
        gy = random()
        base = interf.Base(x, y, 100, 100, None, None)
        test_data = (
            (gx, gy, w, p),
            (gx, gy, w, p + 0.5), )
        for p in test_data:
            base.addPoint(*p)
        return base

#    class TwentyRandomPoints(XRandomPoints(20)): pass

    class SpecificPoints(PointTests):
        def topic(self, base):
            test_points = ((0, 0), (0, base.y - 1),
                    (base.x / 2, base.y / 2),
                    (base.x - 1, 0), (base.x - 1, base.y - 1), )
            for p in test_points:
                yield (base, p)
