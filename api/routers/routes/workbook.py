import asyncio
import importlib
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import json
import urllib
import uuid

from api.config import get_settings, get_db, AioWrap
from api.queries.user_queries import get_user
from api.queries.workbook_queries import (
  workbook_by_id,
  workbooks_by_user_id,
  all_workbooks,
  clone_workbook,
  save_workbook,
  workbook_by_commit
)

from api.db.models import (
  User as DBUser,
  Workbook as DBWorkbook,
  Variation as DBVariation
)

from api.routers import schemas
from api.routers.helpers import get_user_from_header
from api.routers.auth import get_current_active_user

from api.transform import rehydrate_legacy_json

from model.data_handler import DataHandler

from solution import factory, factory_2

from functools import lru_cache

settings = get_settings()
router = APIRouter()
default_provider = settings.default_provider

@router.get("/workbook/{id}")
async def get_workbook_by_id(id: int, db: Session = Depends(get_db)):
  return workbook_by_id(db, id)

@router.get("/workbooks/{user_id}")
async def get_all_workbooks_by_user(user_id: int, db: Session = Depends(get_db)):
  return workbooks_by_user_id(db, user_id)

@router.get("/workbooks/")
async def get_all_workbooks(db: Session = Depends(get_db)):
  return all_workbooks(db)

@router.post("/workbook/{id}")
async def fork_workbook(
    id: int,
    db_active_user: DBUser = Depends(get_current_active_user),
    db: Session = Depends(get_db)):

    cloned_workbook = clone_workbook(db, id)
    cloned_workbook.author_id = db_active_user.id
    saved_workbook = save_workbook(db, cloned_workbook)
    return saved_workbook.id

@router.post("/workbook/")
async def create_workbook(
  workbook: schemas.WorkbookNew,
  db_active_user: DBUser = Depends(get_current_active_user),
  db: Session = Depends(get_db)):

  dbworkbook = DBWorkbook(
    name = workbook.name,
    author_id = db_active_user.id,
    ui = workbook.ui,
    start_year = workbook.start_year,
    end_year = workbook.end_year,
    variations = workbook.variations
  )

  saved_workbook = save_workbook(db, dbworkbook)
  return saved_workbook.id

@router.patch("/workbook/{id}")
async def update_workbook(
  id: int,
  workbook_edits: schemas.WorkbookPatch,
  db_active_user: DBUser = Depends(get_current_active_user),
  db: Session = Depends(get_db)):

  active_user_workbooks = list(filter(lambda w: w.id == id, db_active_user.workbooks))
  if len(active_user_workbooks) == 0:
    raise HTTPException(status_code=400, detail="Workbook not found")

  db_workbook = active_user_workbooks[0]
  workbook_edits_dict = dict(workbook_edits)
  for key in workbook_edits_dict:
    value = workbook_edits_dict[key]
    if value is not None:
      db_workbook.__setattr__(key, value)
  try:
    saved_db_workbook = save_workbook(db, db_workbook)
    return saved_db_workbook
  except:
    raise HTTPException(status_code=400, detail="Invalid Request")

async def calc(constructor, input):
    return to_json(constructor(input))

@lru_cache()
@router.get("/calculate/{workbook_commit_id}")
async def calculate(workbook_commit_id: str, client: AioWrap = Depends(AioWrap), db: Session = Depends(get_db)):
  workbook = workbook_by_commit(db, workbook_commit_id)
  if workbook is None:
    raise HTTPException(status_code=400, detail="Workbook not found")
  for variation_path in workbook.variations:
    variation_data = await client(variation_path)
    scenario_parent_path = variation_data['data']['scenario_parent_path']
    reference_parent_path = variation_data['data']['reference_parent_path']
    scenario_data = await client(scenario_parent_path)
    reference_data = await client(reference_parent_path)
    jsons = list(map(lambda tech: {
        'tech': tech,
        'json': rehydrate_legacy_json(
          tech,
          scenario_data['data'],
          reference_data['data'],
          variation_data['data'])
        }
      , scenario_data['data']['technologies']))
    jsons = list(filter(lambda json: json['tech'] != 'fossilfuelelectricity', jsons))
    constructors = factory_2.all_solutions_scenarios(jsons)
    results = {}
    tasks = []
    for constructor in constructors:
        name = list(filter(lambda json: json['tech'] == constructor, jsons))[0]['json']['name']
        tasks.append(calc(constructors[constructor][0], name))

    results = await asyncio.wait(tasks)
    return [r._result for r in results[0]]

@router.get("/test_diffs/{workbook_id}")
async def compare_with_files(workbook_id: int, db: Session = Depends(get_db)):
  workbook = workbook_by_id(db, workbook_id)
  for variation_path in workbook.variations:
    with urllib.request.urlopen(variation_path) as url:
      variation_data: schemas.Resource = json.loads(url.read().decode())
      scenario_parent_path = variation_data['data']['scenario_parent_path']
      reference_parent_path = variation_data['data']['reference_parent_path']
      with urllib.request.urlopen(scenario_parent_path) as url:
        scenario_data = json.loads(url.read().decode())
        with urllib.request.urlopen(reference_parent_path) as url:
          reference_data = json.loads(url.read().decode())
          jsons = list(map(lambda tech: {
              'tech': tech,
              'json': rehydrate_legacy_json(
                tech,
                scenario_data['data'],
                reference_data['data'])
              }
            , scenario_data['data']['technologies']))
          jsons = list(filter(lambda json: json['tech'] != 'fossilfuelelectricity', jsons))

          constructors = factory.all_solutions_scenarios()
          results2 = {}
          for constructor in constructors:
              names = list(filter(lambda json: json['tech'] == constructor, jsons))
              if len(names) > 0:
                name = names[0]['json']['name']
                obj = constructors[constructor][0](name)
                results2[constructor] = to_json(obj)
          return results2

def to_json(scenario):
    json_data = dict()
    json_data['name'] = scenario.name
    instance_vars = vars(scenario).keys()
    for iv in instance_vars:
        try:
            obj = getattr(scenario, iv)
            if issubclass(type(obj), DataHandler):
                json_data[iv] = obj.to_json()
        except BaseException as e:
            json_data[iv] = None
    return json_data