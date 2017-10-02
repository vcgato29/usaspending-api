import logging
import timeit
from datetime import datetime
from django.core.management.base import BaseCommand
from django.db import connections, transaction as db_transaction
from usaspending_api.etl.broker_etl_helpers import dictfetchall
from django_bulk_update.helper import bulk_update

from usaspending_api.awards.models import TransactionNormalized
from usaspending_api.references.models import RefCountryCode, Location

logger = logging.getLogger('console')
exception_logger = logging.getLogger("exceptions")

country_code_map = {country.country_code: country for country in RefCountryCode.objects.all()}

BATCH_SIZE = 10000

def update_country_code(d_file, location, country_code, state_code=None, state_name=None, place_of_performance_code=None):
    updated_location_country_code = country_code

    # For only FABS
    if d_file == "d2":
        # If the recipient's location country code is empty or it's 'UNITED STATES
        # OR the place of performance location country code is empty and the performance code isn't 00FORGN
        # OR the place of performance location country code is empty and there isn't a performance code
        # THEN we can assume that the location country code is 'USA'
        if (location.recipient_flag and (country_code is None or country_code == 'UNITED STATES')) or \
                                (location.place_of_performance_flag and country_code is None and place_of_performance_code and place_of_performance_code != '00FORGN') or \
                                (location.place_of_performance_flag and country_code is None and not place_of_performance_code):
            updated_location_country_code = 'USA'

    location.location_country = country_code_map.get(updated_location_country_code, None)

    if location.location_country:
        location.location_country_code = location.location_country
        location.country_name = location.location_country.country_name

    location.state_name = state_name if state_name else None
    location.state_code = state_code if state_code else None

    return location

class Command(BaseCommand):
    help = "Create Locations from Location data in the Broker."

    @staticmethod
    def update_location_transaction_assistance(db_cursor, fiscal_year=2017, page=1, limit=500000, save=True):

        list_of_columns = (', '.join(['fain', 'uri', 'award_modification_amendme', 'legal_entity_country_code',
                                      'place_of_perform_country_c', 'place_of_performance_code',
                                      'legal_entity_state_code', 'legal_entity_state_name', 'place_of_perform_state_nam']))

        # get the transaction values we need

        query = "SELECT {} FROM published_award_financial_assistance".format(list_of_columns)
        arguments = []

        fy_begin = '10/01/' + str(fiscal_year - 1)
        fy_end = '09/30/' + str(fiscal_year)

        if fiscal_year:
            if arguments:
                query += " AND"
            else:
                query += " WHERE"
            query += ' action_date::Date BETWEEN %s AND %s'
            arguments += [fy_begin]
            arguments += [fy_end]
        query += ' ORDER BY published_award_financial_assistance_id LIMIT %s OFFSET %s'
        arguments += [limit, (page - 1) * limit]

        logger.info("Executing query on Broker DB => " + query % (arguments[0], arguments[1],
                                                                  arguments[2], arguments[3]))

        db_cursor.execute(query, arguments)

        logger.info("Running dictfetchall on db_cursor")
        award_financial_assistance_data = dictfetchall(db_cursor)

        logger.info("Getting total rows")
        total_rows = len(award_financial_assistance_data)  # - rows_loaded

        logger.info("Processing " + str(total_rows) + " rows of location data")

        pop_bulk = []
        lel_bulk = []

        start_time = datetime.now()

        trans_queryset = TransactionNormalized.objects.prefetch_related('award', 'recipient__location')

        for index, row in enumerate(award_financial_assistance_data, 1):
                if not (index % 100):
                    logger.info('Location Fix: Fixing row {} of {} ({})'.format(str(index),
                                                                                 str(total_rows),
                                                                                 datetime.now() - start_time))
                # Could also use contract_data__fain
                transaction = trans_queryset.filter(award__fain=row['fain'],award__uri=row['uri'],modification_number=row['award_modification_amendme']).first()
                if not transaction:
                    logger.info('Couldn\'t find transaction with fain ({}), uri({}), and modification_number({}). Skipping.'.format(row['fain'], row['uri'], row['award_modification_amendme']))
                    continue

                if transaction.recipient and transaction.recipient.location:
                    lel = transaction.recipient.location
                    location_country_code = row['legal_entity_country_code']
                    state_code = row['legal_entity_state_code']
                    state_name = row['legal_entity_state_name']
                    lel = update_country_code("d2", lel, location_country_code, state_code, state_name)
                    lel_bulk.append(lel)

                if transaction.place_of_performance:
                    pop = transaction.place_of_performance
                    location_country_code = row['place_of_perform_country_c']
                    place_of_perform_code = row['place_of_performance_code']
                    state_name = row['place_of_perform_state_nam']
                    pop = update_country_code("d2", pop, location_country_code, state_code, state_name, place_of_performance_code=place_of_perform_code)
                    pop_bulk.append(pop)

        with db_transaction.atomic():

            pop_update_fields = ['location_country_code', 'place_of_perform_code', 'state_name',
                                 'location_country_code',
                                 'country_name']
            lel_update_fields = ['location_country_code', 'state_code', 'state_name', 'location_country_code',
                                 'country_name']

            logger.info('Bulk creating POP Locations (batch_size: {})...'.format(BATCH_SIZE))
            bulk_update(pop_bulk, update_fields=pop_update_fields, batch_size=BATCH_SIZE)

            logger.info('Bulk creating LE Locations (batch_size: {})...'.format(BATCH_SIZE))
            bulk_update(lel_bulk, update_fields=lel_update_fields, batch_size=BATCH_SIZE)


    @staticmethod
    def update_location_transaction_contract(db_cursor, fiscal_year=None, page=1, limit=500000, save=True):

        list_of_columns = (', '.join(['piid', 'award_modification_amendme', 'legal_entity_country_code',
                                      'place_of_perform_country_c', 'legal_entity_state_code', 'place_of_performance_state']))

        query = "SELECT {} FROM detached_award_procurement".format(list_of_columns)
        arguments = []

        fy_begin = '10/01/' + str(fiscal_year - 1)
        fy_end = '09/30/' + str(fiscal_year)

        if fiscal_year:
            if arguments:
                query += " AND"
            else:
                query += " WHERE"
            query += ' action_date::Date BETWEEN %s AND %s'
            arguments += [fy_begin]
            arguments += [fy_end]
        query += ' ORDER BY detached_award_procurement_id LIMIT %s OFFSET %s'
        arguments += [limit, (page - 1) * limit]

        logger.info("Executing query on Broker DB => " + query % (arguments[0], arguments[1],
                                                                  arguments[2], arguments[3]))

        db_cursor.execute(query, arguments)

        logger.info("Running dictfetchall on db_cursor")
        procurement_data = dictfetchall(db_cursor)

        logger.info("Getting total rows")
        # rows_loaded = len(current_ids)
        total_rows = len(procurement_data)  # - rows_loaded

        logger.info("Processing " + str(total_rows) + " rows of procurement data")

        # bulk_array = []

        start_time = datetime.now()
        for index, row in enumerate(procurement_data, 1):
            with db_transaction.atomic():

                if not (index % 100):
                    logger.info('D1 File Fix: Fixing row {} of {} ({})'.format(str(index),
                                                                                 str(total_rows),
                                                                                 datetime.now() - start_time))

                transaction = TransactionNormalized.objects.filter(award__piid=row['piid'],modification_number=row['award_modification_amendme']).first()
                if not transaction:
                    logger.info('Couldn\'t find transaction with piid ({}) and modification_number({}). Skipping.'.format(row['piid'], row['award_modification_amendme']))
                    continue

                if transaction.recipient and transaction.recipient.location:
                    lel = transaction.recipient.location
                    location_country_code = row['legal_entity_country_code']
                    state_code = row['legal_entity_state_code']
                    lel = update_country_code("d1", lel, location_country_code, state_code)
                    lel.save()

                if transaction.place_of_performance:
                    pop = transaction.place_of_performance
                    location_country_code = row['place_of_perform_country_c']
                    state_code = row['place_of_performance_state']
                    pop = update_country_code("d1", pop, location_country_code, state_code)
                    pop.save()

        logger.info('saving locations')
        # logger.info('BULK ARRAY: '.format(bulk_array))

    def add_arguments(self, parser):

        parser.add_argument(
            '--fiscal_year',
            dest="fiscal_year",
            nargs='+',
            type=int,
            help="Year for which to run the historical load"
        )

        parser.add_argument(
            '--assistance',
            action='store_true',
            dest='assistance',
            default=False,
            help='Runs the historical loader only for Award Financial Assistance (Assistance/FABS) data'
        )

        parser.add_argument(
            '--contracts',
            action='store_true',
            dest='contracts',
            default=False,
            help='Runs the historical loader only for Award Procurement (Contract/FPDS) data'
        )

        parser.add_argument(
            '--page',
            dest="page",
            nargs='+',
            type=int,
            help="Page for batching and parallelization"
        )

        parser.add_argument(
            '--limit',
            dest="limit",
            nargs='+',
            type=int,
            help="Limit for batching and parallelization"
        )
        parser.add_argument(
            '--save',
            dest="save",
            default=True,
            help="Decides if the save method is called after loading"
        )

    # @transaction.atomic
    def handle(self, *args, **options):
        logger.info('Starting historical data load...')

        db_cursor = connections['data_broker'].cursor()
        fiscal_year = options.get('fiscal_year')
        page = options.get('page')
        limit = options.get('limit')
        save = options.get('save')

        if fiscal_year:
            fiscal_year = fiscal_year[0]
            logger.info('Processing data for Fiscal Year ' + str(fiscal_year))
        else:
            fiscal_year = 2017

        page = page[0] if page else 1
        limit = limit[0] if limit else 500000

        if not options['assistance']:
            logger.info('Starting D1 historical data location insert...')
            start = timeit.default_timer()
            self.update_location_transaction_contract(db_cursor=db_cursor, fiscal_year=fiscal_year, page=page, limit=limit, save=save)
            end = timeit.default_timer()
            logger.info('Finished D1 historical data location insert in ' + str(end - start) + ' seconds')

        if not options['contracts']:
            logger.info('Starting D2 historical data location insert...')
            start = timeit.default_timer()
            self.update_location_transaction_assistance(db_cursor=db_cursor, fiscal_year=fiscal_year, page=page, limit=limit, save=save)
            end = timeit.default_timer()
            logger.info('Finished D2 historical data location insert in ' + str(end - start) + ' seconds')

        logger.info('FINISHED')