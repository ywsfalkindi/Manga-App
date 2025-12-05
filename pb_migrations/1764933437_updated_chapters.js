/// <reference path="../pb_data/types.d.ts" />
migrate((app) => {
  const collection = app.findCollectionByNameOrId("pbc_2272205672")

  // add field
  collection.fields.addAt(3, new Field({
    "cascadeDelete": false,
    "collectionId": "pbc_218332259",
    "hidden": false,
    "id": "relation1383608732",
    "maxSelect": 1,
    "minSelect": 0,
    "name": "series_id",
    "presentable": false,
    "required": false,
    "system": false,
    "type": "relation"
  }))

  return app.save(collection)
}, (app) => {
  const collection = app.findCollectionByNameOrId("pbc_2272205672")

  // remove field
  collection.fields.removeById("relation1383608732")

  return app.save(collection)
})
